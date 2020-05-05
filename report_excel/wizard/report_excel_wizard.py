# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from odoo import api, fields, models, _
from odoo.osv.orm import setup_modifiers
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, pycompat
from lxml import etree
import logging
_logger = logging.getLogger(__name__)
class ReportExcelWizard(models.TransientModel):
    _name = 'report_excel_wizard'
    _description = "Report Wizard"
    def _compute_report_name(self):
        return self.env['report.excel'].search([('id', '=', self.env.context.get('id'))])['name']
    def _compute_report_description(self):
        return self.env['report.excel'].search([('id', '=', self.env.context.get('id'))])['description']
    def _compute_report_conf(self):
        return self.env.context.get('id')
    report_conf = fields.Many2one('report.excel', 'Report Excel', required=True, ondelete='cascade', readonly=True, default=_compute_report_conf)
    report_name = fields.Char(string="Report Name", readonly=True, default=_compute_report_name)
    report_description = fields.Text(string="Type of document", readonly=True, default=_compute_report_description)
    data = fields.Serialized()
    @api.multi
    def export_excel(self):
        if len(self.env.context.get('active_ids', [])):
            active_ids = self.env.context.get('active_ids', [])
        else:
            active_ids = []
        datas = {'ids': active_ids}
        datas['active_model'] = self.env.context.get('active_model')
        res = self.read(['report_conf'])
        res = res and res[0] or {}
        if not res:
            return
        res['report_conf_id'] = res['report_conf'][0]
        res_data = self.read(['data'])
        res_data = res_data and res_data[0] or {}
        datas['form'] = res
        datas['form']['data'] = res_data['data']
        datas['send_by_email'] = self.env.context.get('send_by_email')        
        return self.env['report_excel_gen'].create_xls(datas, CellUtil)
    @api.multi
    def wizard_view(self):
        return {'name': _('Report Excel'),
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('report_excel.view_report_excel_wizard').id,
                'res_model': 'report_excel_wizard',
                'src_model': 'report',
                'type': 'ir.actions.act_window',
                'target': 'new',
                }
    @api.model
    def create(self, values):
        result = super(ReportExcelWizard, self).create(values)
        for key, val in result._fields.items():
            field = val
            key_split = key.split('_')
            if len(key_split) > 2:
                if key_split[0] == 'x' and key_split[1] == 'param' and int(key_split[2]) == self._context.get('id'):
                    field.inverse = 'compute_'
        if len(values):
            for k,v in list(values.items()):
                if k != 'data':
                    self.compute_(self._fields[k], result, v)
        return result
    @api.multi
    def write(self, vals):
        record = self
        result = super(ReportExcelWizard, self).write(vals)           
        if len(vals):
            for k,v in list(vals.items()):
                if k != 'data':
                    self.compute_(self._fields[k], record, v)
        self._compute(record)
        return result
    @api.multi
    def _compute(self, records=None):
        records = self if not records else records
        for record in records:
            for key, val in list(record._fields.items()):
                key_split = key.split('_')
                if len(key_split) > 2:
                    if key_split[0] == 'x' and key_split[1] == 'param' and int(key_split[2]) == record.env.context.get('id'):
                        field = record._fields.get(key)
                        values = record['data']
                        value = values.get(field.name)
                        rec_val = field.convert_to_read(record[field.name], record, use_name_get=False)
                        if type(rec_val) is date:
                            rec_val = rec_val.strftime(DEFAULT_SERVER_DATE_FORMAT)
                        if type(rec_val) is datetime:
                            rec_val = rec_val.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        if isinstance(rec_val, list) and value is not None:
                            value.sort()
                            rec_val.sort()
                        if rec_val != value and field.name in values:
                            if isinstance(rec_val, list):
                                record[field.name] = [[6, False, values.get(field.name)]]
                            else:
                                record[field.name] = values.get(field.name)
                            if field.relational:
                                record[field.name] = record[field.name].exists()
    def compute_(self, field=None, records=None, val=None):
        if records:
            for record in records:
                values = record['data']
                if isinstance(val, list):
                    value = val[0][2] if val else val
                else:
                    value = val
                if type(val) is date:
                    value = val.strftime(DEFAULT_SERVER_DATE_FORMAT)
                if type(val) is datetime:
                    value = val.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                if value:
                    if isinstance(value, list) and values.get(field.name) is not None:
                        if sorted(values.get(field.name)) != sorted(value):
                            values[field.name] = value
                            record['data'] = values
                    else:
                        if values.get(field.name) != value:
                            values[field.name] = value
                            record['data'] = values
                else:
                    if field.name in values:
                        values.pop(field.name)
                        record['data'] = values
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ReportExcelWizard, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if 'model' in self.env.context and self.env.context.get('model') == 'report.excel':
            eview = etree.fromstring(res['arch'])
            placeholder = eview.xpath("group[@name='placeholder']")
            if len(placeholder):
                placeholder = placeholder[0]
                params = self.env['report.excel.param'].search([('report_excel_id', '=', self.env.context.get('id'))])            
                if params:
                    for param in params:
                        param_field = self.env['ir.model.fields'].search([('id', '=', param.wizard_param_ir_model_field_id.id )])
                        if len(param_field):
                            name = param_field['name']
                            name_split = name.split('_')
                            if len(name_split) > 2:
                                if name_split[0] == 'x' and name_split[1] == 'param':
                                    if param_field.ttype == 'many2one':
                                        node = etree.SubElement(placeholder, 'field', {'name': name, 'options':"{'no_open': True, 'no_create': True}"})
                                    elif param_field.ttype == 'many2many':
                                        node = etree.SubElement(placeholder, 'field', {'name': name, 'widget':"many2many_tags", 'options':"{'no_open': True, 'no_create': True}"})
                                    else:
                                        node = etree.SubElement(placeholder, 'field', name=name)
            if self.env['report.excel'].browse(self.env.context.get('id')).send_email:
                node_button_print = eview.xpath(".//button[@name='export_excel']")[0]
                node_footer = node_button_print.getparent()
                node_footer.insert(node_footer.index(node_button_print)+1, etree.SubElement(node_footer, 'button', {'name': 'export_excel',  'string': 'Send by Email',  'type':'object', 'class':'btn-primary', 'context':'{"send_by_email": True}'}))
            try:
                xarch, xfields  = self.env['ir.ui.view'].postprocess_and_fields(self._name, eview, None)
            except ValueError:
                return res                                    
            res_fields = res.get('fields')
            for key, val in list(xfields.items()):
                if key not in res_fields:
                    res_fields[key] = val  
            res['arch'] = etree.tostring(eview, encoding='unicode')
        return res
class CellUtils(object):
    def __init__(self):
        self._COL_STRING_CACHE = {}
        self._STRING_COL_CACHE = {}
        for i in range(1, 18279):
            col = self._get_column_letter(i)
            self._STRING_COL_CACHE[i] = col
            self._COL_STRING_CACHE[col] = i
    def _get_column_letter(self, col_idx):
        if not 1 <= col_idx <= 18278:
            raise ValueError("Invalid column index {0}".format(col_idx))
        letters = []
        while col_idx > 0:
            col_idx, remainder = divmod(col_idx, 26)
            if remainder == 0:
                remainder = 26
                col_idx -= 1
            letters.append(chr(remainder+64))
        return ''.join(reversed(letters))
CellUtil = CellUtils()
