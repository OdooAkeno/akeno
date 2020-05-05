# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2018 GRIMMETTE,LLC <info@grimmette.com>

import base64
import re
from datetime import datetime
from collections import Counter
from copy import deepcopy
from odoo import api, fields, models, tools, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_utils
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import logging
_logger = logging.getLogger(__name__)
MAP_HAVING_OPERATOR = {
        "=":    "IS EQUAL TO",
        "!=":   "IS NOT EQUAL TO",
        ">":    "GREATER THAN",
        "<":    "LESS THAN",
        ">=":   "GREATER THAN OR EQUAL TO",
        "<=":   "LESS THAN OR EQUAL TO",
}
class ReportExcel(models.Model):
    _name = "report.excel"
    _description = "Report Excel"
    _order = "name,id"
    _disallowed_datetime_patterns = list(tools.DATETIME_FORMATS_MAP.keys())
    _disallowed_datetime_patterns.remove('%y')
    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', help="If unchecked, it will allow you to hide the report excel without removing it.", default=True)
    out_file_name = fields.Char(string='Output File Name', default="'Report_%d-%m-%Y'", help="The file name. See bellow Legends for supported Date and Time Formats.")
    data = fields.Binary('Template', attachment=True)
    doc_count = fields.Integer(compute='_compute_attached_docs_count', string="Number of documents attached")
    datas_fname = fields.Char(compute='_compute_attached_doc_name', string='File Name')
    template_name_id = fields.Many2one(comodel_name="ir.attachment", string="Template File Excel", required=False,
                                   help="This field holds the Excel template used as template for the this document. You must upload the template files.\nIf no template is selected, the default template will be used.",
                                   domain = "[('res_model', '=', 'report.excel'), ('res_id', '=', id)]", copy=False
                                   )
    sheet_reference = fields.Char('Sheet Name', required=True, default='Sheet1',
                                  help="The Sheet Name must correspond to the Sheet Name in the Excel Workbook on which the report will be displayed."
                                  ) 
    description = fields.Text('Displayed Description', help="This description is displayed in the wizard form when you print the report.")
    description_report = fields.Text('Description')
    root_model_id = fields.Many2one('ir.model', string='Root Model', ondelete='cascade', required=True)
    ir_values_id = fields.Many2one('ir.actions.act_window', string='More Menu entry', readonly=True,
                                   help='More menu entry.', copy=False)
    show_level = fields.Boolean('Show Row Level', default=False)
    show_autofilter = fields.Boolean('Show Autofilter', default=False)
    report_excel_param_ids = fields.One2many('report.excel.param', 'report_excel_id', string='Report Parameters', copy=False)
    report_id = fields.Integer(compute='_compute_id', string="Report id", store=False)
    report_excel_param_content = fields.Char(compute='_compute_report_excel_param_content', string="Report Parameters", store=False)
    report_excel_section_ids = fields.One2many('report.excel.section', 'report_excel_id', string='Report Sections', copy=True)
    send_email = fields.Boolean('Allow Email', help="Allow sending report by email.", default=False)
    email_template_id = fields.Many2one(comodel_name="mail.template", string="Email Template", required=False,
                                   help="This field contains the Email Template that will be used by default when sending this report.",
                                   copy=True
                                   )
    @api.multi
    def attachment_doc_view(self):
        self.ensure_one()
        domain = [
            '&', ('res_model', '=', self._name), ('res_id', 'in', self.ids)]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'help': _('''<p class="oe_view_nocontent_create">
                        Excel templates.</p><p>
                        Prepare and upload the template file in MS Excel format.
                    </p>'''),
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }
    def _compute_attached_docs_count(self):
        Attachment = self.env['ir.attachment']
        for doc in self:
            doc.doc_count = Attachment.search_count([
                '&', ('res_model', '=', 'report.excel'), ('res_id', '=', doc.id)
            ])
    @api.model
    @api.depends('data')
    def _compute_attached_doc_name(self):
        Attachment = self.env['ir.attachment']
        datafile = Attachment.search_read([
            '&', ('res_model', '=', 'report.excel'), ('res_id', '=', self.id), ('res_field', '=', 'data')
            ])
        if datafile:
            return datafile[0]['datas_fname']
    def _compute_id(self):
        self.report_id = self.id 
    @api.depends('report_excel_param_ids')
    def _compute_report_excel_param_content(self):
        params = ''
        if isinstance(self.id, models.NewId):
            self.report_excel_param_content = params
        else:
            param_ids = self.env['report.excel.param'].search([('report_excel_id', '=', self.id)])
            for i in param_ids:
                rel_model = 'false'
                if i.param_ir_model_id.model:
                     rel_model = i.param_ir_model_id.model
                params =''.join([params,'param(',i.code,'),',i.name,',',i.type_param,',',rel_model,';']) 
            self.report_excel_param_content = params
    @api.multi
    def create_action(self):
        for report in self:
            context_report1 = "{'model': 'report.excel', 'id': %d}" % (report.id,)
            context_report2 = "{'id': %d, 'model': 'report.excel'}" % (report.id,)
            action_id = self.env['ir.actions.act_window'].search(["&",('res_model', '=', 'report_excel_wizard'),"|",('context', '=', context_report1),('context', '=', context_report2)]).id
            if action_id:
                action = self.env['ir.actions.act_window'].search([('id', '=', action_id)])
                action.name = report.name
                vals = {
                   'binding_model_id': report.root_model_id.id,
                   'binding_type': 'report',
                }
                action.write(vals)
            else:
                 view_id = self.env['ir.ui.view'].search([('model', '=', 'report_excel_wizard')]).id
                 vals = {
                     'name': report.name,
                     'res_model': 'report_excel_wizard',
                     'src_model': 'report.excel',
                     'view_mode': 'form',
                     'target': 'new',
                     'view_type':"form",
                     'view_id': view_id,
                     'context': {
                         'model': 'report.excel',
                         'id': report.id,
                     },
                    'binding_model_id': report.root_model_id.id,
                    'binding_type': 'report',
                 }
                 action = self.env['ir.actions.act_window'].create(vals)
            report.write({'ir_values_id': action.id})
        return {'type': 'ir.actions.act_window_close'}
    @api.multi
    def unlink_action(self):
        self.check_access_rights('write', raise_exception=True)
        for report in self:
            if report.ir_values_id:
                vals = {
                   'binding_model_id': False,
                   'binding_type': 'action',
                }
                report.ir_values_id.write(vals)
                report.write({'ir_values_id': False})
        return True
    @api.onchange('root_model_id')
    def _change_sub_root_model_id(self):
        self.report_excel_section_ids = [(2, line_id, False) for line_id in self.report_excel_section_ids.ids]        
        self.email_template_id = False
    @api.multi
    def map_params(self, new_report_id):
        reports = self.env['report.excel.param']
        for param in self.report_excel_param_ids:
            defaults = {
                'name': param.name,                
                'code': param.code,                
                'type_param': param.type_param,                
                'param_ir_model_id': param.param_ir_model_id.id, 
                'wizard_param_ir_model_field_id': False,
                'report_excel_id': new_report_id,                
                }
            reports += param.copy(defaults)
        return self.browse(new_report_id).write({'report_excel_param_ids': [(6, 0, reports.ids)]})
    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_('%s (copy)') % self.name)
        report = super(ReportExcel, self).copy(default)
        if 'report_excel_param_ids' not in default:
            self.map_params(report.id)
            self.env.cr.execute("""
                    WITH RECURSIVE r AS (
                       SELECT id, parent_id
                       FROM report_excel_section
                       WHERE report_excel_id = %s
                       UNION
                       SELECT report_excel_section.id, report_excel_section.parent_id
                       FROM report_excel_section
                          JOIN r
                              ON report_excel_section.parent_id = r.id
                    )
                    SELECT * FROM r                         
                   """ % (report.id,))
            cr = self.env.cr.fetchall()
            cr_ids = [x[0] for x in cr]            
            if len(cr_ids):
                for i in self.report_excel_param_ids:
                    for n in report.report_excel_param_ids:
                        if n.code == i.code:
                             new_id = n.id
                             break
                    query = """
                        UPDATE report_excel_fields 
                        SET having_param_id = %s 
                        WHERE having_param_id = %s AND report_excel_section_id IN %s
                    """
                    self.env.cr.execute(query, [new_id, i.id, tuple(cr_ids)])
                    self.invalidate_cache()
        return report
    @api.model
    def create(self, vals):
        if not self.id:
            report_tmp = super(ReportExcel, self).create(vals)                     
            check_test, check_text = self.check_report(report_tmp)  
            super(ReportExcel, report_tmp).unlink()
            if check_test:
                raise UserError(_(check_text))       
        res = super(ReportExcel, self).create(vals)
        if 'report_excel_param_ids' in vals:
            wizard_model_id = self.env['ir.model'].search([('model','=', 'report_excel_wizard')],[]).id
            vals_update = {'report_excel_param_ids':[]} 
            for param_id in res.report_excel_param_ids:
                if param_id.wizard_param_ir_model_field_id.id == False:
                    seq_number = self.env['ir.sequence'].next_by_code('report.excel')
                    vals_create = {
                        'name':''.join(['x_param_', str(res.id),'_' , str(param_id.id),'_' , str(seq_number)]),
                        'model_id':wizard_model_id,
                        'field_description':param_id.display_name,
                        'ttype':param_id.type_param,
                        'store':False,
                        'domain':None,
                        'selection':None,
                        'on_delete':None,
                        'required':param_id.param_required,
                        'compute':'self._compute()'
                        }
                    if param_id.param_ir_model_id.id != False:
                        vals_create["relation"] = self.env['ir.model'].search([('id','=', param_id.param_ir_model_id.id)],[]).model
                        if param_id.type_param == 'many2one':    
                            vals_create["on_delete"] = 'cascade'
                        if param_id.type_param == 'many2many':
                            vals_create["relation_table"] = ''.join(['x_rew_', str(res.id),'_' , str(param_id.id),'_' , str(seq_number),'_rel' ])
                    record = self.env['ir.model.fields'].create(vals_create)
                    vals_update['report_excel_param_ids'].append([1, param_id.id, {'wizard_param_ir_model_field_id': record.id}])
            if len(vals_update['report_excel_param_ids']): 
                super(ReportExcel, res).write(vals_update)
        return res
    @api.one
    @api.model    
    def write(self, vals):
        wizard_model_id = self.env['ir.model'].search([('model','=', 'report_excel_wizard')],[]).id
        wizard_data_field_id = self.env['ir.model.fields'].search([('name','=', 'data'), ('model_id','=', wizard_model_id)],[]).id
        vals_update_before = {'report_excel_param_ids':[]}
        if 'report_excel_param_ids' in vals:
            unlink_ir_model_fields_ids = [] 
            for param in vals['report_excel_param_ids']:
                if param[0] in [1,2,3,5]:
                    vals_update_before['report_excel_param_ids'].append([1, param[1], {'wizard_param_ir_model_field_id': False}])                    
                    unlink_ir_model_fields_ids.append(
                        self.env['ir.model.fields'].search([('name','like',  ''.join(['x_param_', str(self.id),'_' , str(param[1])])), ('model_id','=', wizard_model_id)],[]).id                        
                        )
            res = super(ReportExcel, self).write(vals_update_before)
        res = super(ReportExcel, self).write(vals)
        if 'report_excel_param_ids' in vals and vals['report_excel_param_ids'][0][0] == 6:
            pass
        else:
            check_test, check_text = self.check_report()  
            if check_test:
                raise UserError(_(check_text))   
        if 'report_excel_param_ids' in vals:
            vals_update = {'report_excel_param_ids':[]} 
            for param_id in self.report_excel_param_ids:
                if param_id.wizard_param_ir_model_field_id.id == False:
                    seq_number = self.env['ir.sequence'].next_by_code('report.excel')
                    vals_create = {
                        'name':''.join(['x_param_', str(self.id),'_' , str(param_id.id),'_' , str(seq_number)]),
                        'model_id':wizard_model_id,
                        'field_description':param_id.display_name,
                        'ttype':param_id.type_param,
                        'store':False,
                        'domain':None,
                        'selection':None,
                        'on_delete':None,
                        'required':param_id.param_required,
                        'compute':'self._compute()',
                        }
                    if param_id.param_ir_model_id.id != False:
                        vals_create["relation"] = self.env['ir.model'].search([('id','=', param_id.param_ir_model_id.id)],[]).model
                        if param_id.type_param == 'many2one':    
                            vals_create["on_delete"] = 'cascade'
                        if param_id.type_param == 'many2many':
                            vals_create["relation_table"] = ''.join(['x_rew_', str(self.id),'_' , str(param_id.id),'_' , str(seq_number),'_rel' ])
                    record = self.env['ir.model.fields'].create(vals_create)
                    vals_update['report_excel_param_ids'].append([1, param_id.id, {'wizard_param_ir_model_field_id': record.id}])
            if len(vals_update['report_excel_param_ids']): 
                res = super(ReportExcel, self).write(vals_update)
            records = self.env['ir.model.fields'].search([('id','in', unlink_ir_model_fields_ids)],[])
            for rec in records:
                if rec.ttype == 'many2many':
                    self.env.cr.execute("DELETE FROM %s WHERE id=%s" % ('ir_model_fields', rec.id))                    
                else:
                    rec.unlink()
        return res
    @api.one
    def unlink(self):
        wizard_param_ir_model_field_ids = [] 
        for param in self.report_excel_param_ids:
            wizard_param_ir_model_field_ids.append(param.wizard_param_ir_model_field_id.id)
        for rec in self:
            context_report1 = "{'model': 'report.excel', 'id': %d}" % (rec.id,)
            context_report2 = "{'id': %d, 'model': 'report.excel'}" % (rec.id,)
            action_id = self.env['ir.actions.act_window'].search(["&",('res_model', '=', 'report_excel_wizard'),"|",('context', '=', context_report1),('context', '=', context_report2)]).id
            if action_id:
                self.env['ir.ui.menu'].search([('action', '=', 'ir.actions.act_window,%d' % (action_id,))]).unlink()
                self.env['ir.actions.act_window'].search(["&",('res_model', '=', 'report_excel_wizard'),"|",('context', '=', context_report1),('context', '=', context_report2)]).unlink()
        res = super(ReportExcel, self).unlink()
        if not len(wizard_param_ir_model_field_ids): 
            records = self.env['ir.model.fields'].search([('name','like', 'x_param_'),('model','=', 'report_excel_wizard')],[])
            for r in records:
                name_spl = r.name.split('_')
                if name_spl[2] == str(self.id):
                    wizard_param_ir_model_field_ids.append(r.id)
        if len(wizard_param_ir_model_field_ids):
            ids_tpl = tuple(wizard_param_ir_model_field_ids)
            self._cr.execute("DELETE FROM ir_model_fields WHERE id in %s", [ids_tpl])
            self.invalidate_cache()
        return res
    def check_report(self, res=None):
        if res is None:
            res = self
        result = False
        msg_err = ''
        code_arr = []
        param_dict = {}
        for p in res.report_excel_param_ids:
            code_arr.append(p.code)
            param_dict[p.code] = {
                'id': p.id,
                'name': p.name,
                'code': p.code,
                'type_param': p.type_param,    
                'param_ir_model_id': p.param_ir_model_id,
                }
        if len(code_arr) > 1:
            dup = [k for k,v in list(Counter(code_arr).items()) if v > 1]
            if len(dup):
                dup.sort()
                for code in dup:
                    msg = '''Duplicated Parameter Code: "%s" !
                           The Parameter Code must be unique within the Report! \n \n ''' % str(code)
                    msg_err = msg_err + msg
                result = True
        if len(res.report_excel_section_ids.ids):
            result_sections, msg_sections_err = self.check_section(res.report_excel_section_ids, param_dict)
            if result_sections:
                msg_err = msg_err + msg_sections_err
                result = True
        return result, msg_err
    def check_section(self, res=None, param_dict=None):
        res = self if res is None else res
        result = False
        msg_err = ''
        section_intersection = {}
        for section in res:
            msg_section_header = '''Section: \"%s\"
            '''  % (section.name,) 
            section_result = False
            msg_section = ''
            section_start_col, section_start_row = CheckCell.coordinate_from_string(section.section_start)
            section_end_col, section_end_row = CheckCell.coordinate_from_string(section.section_end)
            section_start_col_ind = CheckCell.column_index_from_string(section_start_col) 
            section_end_col_ind = CheckCell.column_index_from_string(section_end_col) 
            section_arr = ()
            for c in range(section_start_col_ind, section_end_col_ind + 1):
                for r in range(section_start_row, section_end_row + 1):
                    section_arr += (CheckCell.cell_from_index(c,r),)
            if len(res.ids) > 1:
                for s in res:
                    if section.id != s.id:
                        s_start_col, s_start_row = CheckCell.coordinate_from_string(s.section_start)
                        s_end_col, s_end_row = CheckCell.coordinate_from_string(s.section_end)
                        s_start_col_ind = CheckCell.column_index_from_string(s_start_col) 
                        s_start_end_ind = CheckCell.column_index_from_string(s_end_col) 
                        s_arr = ()
                        for c in range(s_start_col_ind, s_start_end_ind + 1):
                            for r in range(s_start_row, s_end_row + 1):
                                s_arr += (CheckCell.cell_from_index(c,r),)
                        result_intersection = list(set(section_arr) & set(s_arr))
                        if s.id in section_intersection and section.id in section_intersection[s.id]:
                            pass
                        else:
                            if len(result_intersection):
                                result_intersection.sort()
                                result_intersection_str = ''
                                for i in result_intersection:
                                    result_intersection_str = result_intersection_str + i + ", " 
                                msg = '''Incorrect Boundaries of Sections ! 
                                         Section \"%s\":  Start Section: \"%s\",  End Section: \"%s\"  - 
                                         Section \"%s\":  Start Section: \"%s\",  End Section: \"%s\".
                                         Intersection Of Cells: %s 
                                         Section Boundaries should not intersect with other sections of the same level ! \n
                                '''  % (section.name, section.section_start, section.section_end, s.name, s.section_start, s.section_end, result_intersection_str,)                             
                                msg_section = msg_section + msg 
                                result = True
                                section_result = True
                                if section.id in section_intersection: 
                                    section_intersection[section.id].append(s.id)
                                else:
                                    section_intersection[section.id] = [s.id]
            section_field_cell = []
            for field in section.report_excel_fields_ids:
                section_field_cell.append(field.cell)
            for cell in section_field_cell:
                if cell not in section_arr:
                    msg = '''The Report Excel Field \"%s\" cannot be located outside the sections \"%s\"! 
                             The field must be within:  Start Section: \"%s\",  End Section: \"%s\" \n
                    '''  % (cell, section.name, section.section_start, section.section_end,)                             
                    msg_section = msg_section + msg 
                    result = True
                    section_result = True
            for s in section.children_ids:    
                s_start_col, s_start_row = CheckCell.coordinate_from_string(s.section_start)
                s_end_col, s_end_row = CheckCell.coordinate_from_string(s.section_end)
                s_start_col_ind = CheckCell.column_index_from_string(s_start_col) 
                s_start_end_ind = CheckCell.column_index_from_string(s_end_col) 
                s_arr = ()
                for c in range(s_start_col_ind, s_start_end_ind + 1):
                    for r in range(s_start_row, s_end_row + 1):
                        s_arr += (CheckCell.cell_from_index(c,r),)
                result_child_bound = list(set(s_arr) - set(section_arr))
                if len(result_child_bound):
                    msg = '''Incorrect Children Section: \"%s\" ! 
                             Parent Section \"%s\":  Start Section: \"%s\",  End Section: \"%s\"  
                             Children Section \"%s\":  Start Section: \"%s\",  End Section: \"%s\"
                             Child Section Boundaries cannot be outside the Parent Section ! \n
                    '''  % (s.name, section.name, section.section_start, section.section_end, s.name, s.section_start, s.section_end,)                             
                    msg_section = msg_section + msg 
                    result = True
                    section_result = True
                result_intersection = list(set(section_field_cell) & set(s_arr))
                if len(result_intersection):
                    result_intersection.sort()
                    result_intersection_str = ''
                    for i in result_intersection:
                        result_intersection_str = result_intersection_str + i + ", " 
                    msg = '''Incorrect Report Excel Fields: %s !  Section: \"%s\".  
                             Section \"%s\":  Start Section: \"%s\",  End Section: \"%s\"  - 
                             Children Section \"%s\":  Start Section: \"%s\",  End Section: \"%s\".
                             The Report Excel Fields cannot be located inside the Child Sections ! \n
                    '''  % (result_intersection_str, section.name, section.name, section.section_start, section.section_end, s.name, s.section_start, s.section_end,)                             
                    msg_section = msg_section + msg 
                    result = True
                    section_result = True
            if len(section_field_cell) > 1:
                dup = [k for k,v in list(Counter(section_field_cell).items()) if v > 1]
                if len(dup):
                    dup.sort()
                    msg_tmp = ''
                    for cell in dup:
                        msg = '''Duplicated Report Excel Field: \"%s\" ! Section \"%s\" 
                                 The Report Excel Fields must be unique within the Section! \n
                                 ''' % (cell, section.name,)
                        msg_tmp = msg_tmp + msg
                    msg_section = msg_section + msg_tmp 
                    result = True
                    section_result = True
            if section.domain != '[]' and section.domain != False:
                domain_split = re.split(r',', section.domain)
                for sp in domain_split:
                    if 'param(' in sp:
                        sp1 = re.split(r'\(', sp)
                        sp2 = re.split(r'\)', sp1[1])
                        p_code = sp2[0]
                        if p_code not in param_dict:
                            msg = '''Incorrect Domain !  Section: \"%s\".  
                                     Parameter Code \"%s\" does not exist ! 
                            '''  % (section.name, p_code,)                             
                            msg_section = msg_section + msg 
                            result = True
                            section_result = True
            if section_result:
                msg_err = msg_err + msg_section
            result_sections, msg_sections_err = self.check_section(section.children_ids, param_dict)
            if result_sections:
                msg_err = msg_err + msg_sections_err
                result = True
        return result, msg_err
class ReportExcelParam(models.Model):
    _name = "report.excel.param"
    _description = "Report Excel Params"
    _order = "sequence"
    sequence = fields.Integer(default=10, help="Gives the sequence of this line when displaying.")
    report_excel_id = fields.Many2one('report.excel', ondelete='cascade', string='Report excel Reference')
    name = fields.Char('Param Name', required=True)
    code = fields.Char('Code', required=True)
    type_param = fields.Selection([
        ('char', 'Char'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('many2one', 'Many2one'),
        ('many2many', 'Many2many'),
        ('date', 'Date'),
        ('datetime', 'DateTime'),
        ('boolean', 'Boolean'),
    ], string='Param Type', required=True, help="The Param Type of Report.")
    param_ir_model_id = fields.Many2one('ir.model', ondelete='cascade', string='Param Model', domain=[('transient', '=', False)])
    wizard_param_ir_model_field_id = fields.Many2one('ir.model.fields', string='Wizard Param Model Field')
    param_required = fields.Boolean(string='Param Required', help="If checked, the Parameter becomes Mandatory for filling in the Wizard.", default=False)
    @api.model
    @api.onchange('type_param')
    def _update_param_ir_model_id(self):
        self.param_ir_model_id = False
    @api.one
    @api.constrains('code')
    def _check_code(self):
        _code_re = re.compile(r'^[\w\d_-]*$')
        code_string = self.code 
        match = _code_re.match(code_string)
        if not match:
            msg = 'Invalid Parameter Code: "%s" ! In the "Code" are allowed only: Latin Letters, Numbers, Underscore, Dash.' % code_string
            raise ValidationError(msg)
    @api.one
    @api.constrains('param_ir_model_id')
    def _check_param_ir_model_id(self):
        if not self.param_ir_model_id.id and self.type_param in ['many2one', 'many2many'] :
            msg = 'Parameter "%s" - Not filled "Param Model" field!' % self.name
            raise ValidationError(msg)
        return 
class ReportExcelSection(models.Model):
    _name = "report.excel.section"
    _description = "Report Excel Sections"
    _order = "sequence"
    @api.model    
    def _compute_root_model(self):
        if not self._context.get('section'):
            return self._context.get('root_model_id')
    def _get_root_model_related_field_domain(self):
        if self._context.get('section'):
            res = self.env['ir.model.fields'].search([('model_id','=', self._context.get('root_model_id')),('ttype','in', ('many2one','one2many','many2many'))],[])
            if len(res.ids):
                return [('id', 'in', res.ids)]
            else:
                return [('id', 'in', [0])]             
        else:
            return []
    def _get_root_model_domain(self):
        if self._context.get('section'):
            res = self.env['ir.model'].search([('id','=', self._context.get('root_model_id'))],[])
            model_ids = []
            if res:
                relation = []
                model =  res.model
                fields = self.env[model].fields_get()
                for k,v in list(fields.items()):
                    if v.get('relation'):
                        relation.append(v.get('relation'))
                model_ids = self.env['ir.model'].search([('model','in', list(set(relation)))],[]).ids
            if len(model_ids):
                return [('id', 'in', model_ids)]
            else:
                return [('id', 'in', [0])] 
        else:
            return [('id', '=', self._context.get('root_model_id'))]
    @api.model    
    def _compute_root_model_name(self):
        if not self._context.get('section'):
            res = self.env['ir.model'].search([('id','=', self._context.get('root_model_id'))],[])
            if len(res):
                model_name = res.model
                return model_name
    @api.model    
    def _check_root_model(self):
        res = self.env['ir.model'].search([('id','=', self._context.get('root_model_id'))],[])
        if len(res):
            return True
        else:
            if not self._context.get('section'):
                raise UserError(_('Report Root Model is not defined. Before you can define a Section, you must specify a Report Root Model.'))
            else:
                raise UserError(_('Parent Section Field is not defined. Before you can define a Child Section, you must specify a Parent Section Field for this Section.'))
    @api.model    
    def _check_section(self):
        if self._context.get('section'):
            return self._context.get('section')
    @api.model    
    def _default_compute_report_id(self):
        return self._context.get('report_id')
    @api.one
    @api.model    
    def _compute_report_id(self):
        if self._context.get('report_id'):
            self.report_id = self._context.get('report_id')
        else:
            if self.report_excel_id:
                self.report_id = self.report_excel_id.report_id 
            if self.parent_id:
                self.report_id = self.parent_id.report_id 
    @api.model    
    def _default_report_excel_param_content(self):
        return self._context.get('report_excel_param_content')
    @api.one
    @api.model    
    def _compute_report_excel_param_content(self):
        if self._context.get('report_excel_param_content'):
            self.report_excel_param_content = self._context.get('report_excel_param_content')
        else:
            if self.report_excel_id:
                self.report_excel_param_content = self.report_excel_id.report_excel_param_content 
            if self.parent_id:
                self.report_excel_param_content = self.parent_id.report_excel_param_content 
    @api.model    
    def _default_section_level(self):
        if  self._context.get('section_level'):
            return self._context.get('section_level') + 1
        else:
            return 1
    sequence = fields.Integer(default=10, help="Gives the sequence of this line when displaying.")
    name = fields.Char('Section Name', required=True)
    report_excel_id = fields.Many2one('report.excel', string='Report excel Reference', ondelete='cascade')
    parent_id = fields.Many2one('report.excel.section', ondelete='cascade', string='Parent Section')
    children_ids = fields.One2many('report.excel.section', 'parent_id', string='Children Sections', copy=True)
    report_id = fields.Integer(compute='_compute_report_id', string="Report id", default=_default_compute_report_id, store=False)
    report_excel_param_content = fields.Char(compute='_compute_report_excel_param_content', string="Report Parameters", default=_default_report_excel_param_content, store=False)
    type_data = fields.Selection([
        ('data_header', 'Data Header'),
        ('data_line', 'Data Line'),
        ('data_footer', 'Data Footer'),
    ], string='Section Type', required=True, default='data_line', help="The Type Data of Section.")
    level = fields.Integer('Level')
    report_excel_fields_ids = fields.One2many('report.excel.fields', 'report_excel_section_id', string='Report Excel Fields', copy=True)
    root_model_related_field_id = fields.Many2one('ir.model.fields', string='Parent Section Field', 
                                    domain=lambda self: self._get_root_model_related_field_domain(),
                                    ondelete='cascade',
                                    help="The ROOT Model Field in the Parent Section for which the data is detailed in this Section"
                                    )
    root_model_id = fields.Many2one('ir.model', string='Section Root Model', 
                                    default = _compute_root_model, 
                                    domain=lambda self: self._get_root_model_domain(),
                                    ondelete='cascade',
                                    )
    root_model_name = fields.Selection(selection='_list_all_models', string='Report Root Model Name', default=_compute_root_model_name)
    check_root_model = fields.Boolean(string='Check Root Model', default=_check_root_model)
    section = fields.Boolean(string='Check Section', default=_check_section)
    section_level = fields.Integer('Section Level', default=_default_section_level)
    section_start = fields.Char(string='Start Section', required=True, 
                                help='The Upper-Left Cell of the Section. Format e.g. A5. The Beginning and End of the Section must be within the boundaries of the Parent Section! Section borders should not intersect with other sections of the same level!'
                                )
    section_end = fields.Char(string='End Section', required=True, 
                              help='The Lower-Right cell of the Section. Format e.g. G7. The Beginning and End of the Section must be within the boundaries of the Parent Section! Section borders should not intersect with other sections of the same level!'
                              )
    sql_bool = fields.Boolean(string='SQL', default=False)
    sql_statement = fields.Text(string='SQL Statement')
    report_excel_fields_sql_ids = fields.One2many('report.excel.fields.sql', 'report_excel_section_id', string='Report Excel Fields SQL', copy=True)
    domain = fields.Char(string='Domain',default='[]', help="The syntax for using a Report Parameter: param(PARAMETER CODE), for Example: param(ABC). Parameters are available for selection only after saving the Report!")
    description = fields.Text('Description')
    @api.onchange('section_start', 'section_end')
    @api.model
    def _set_upper(self):
        self.section_start = str(self.section_start).upper() if self.section_start else ''
        self.section_end = str(self.section_end).upper() if self.section_end else ''
    @api.onchange('root_model_related_field_id')
    @api.model
    def _onchange_root_model_related_field(self):
        if self._context.get('section'):
            if self.root_model_related_field_id:            
                res = self.env['ir.model'].search([('model','=', self.root_model_related_field_id.relation)],[])
                if len(res):
                    self.root_model_id = res.id            
            else:
                self.root_model_id = False
        else:
            if self.section:
                if self.root_model_related_field_id:            
                    res = self.env['ir.model'].search([('model','=', self.root_model_related_field_id.relation)],[])
                    if len(res):
                        self.root_model_id = res.id            
                else:
                    self.root_model_id = False
    @api.onchange('root_model_id')
    @api.model
    def _set_root_model_name(self):
        if self._context.get('section'):
            if self.root_model_id:
                res = self.env['ir.model'].search([('id','=', self.root_model_id.id)],[])
                if len(res):
                    self.root_model_name = res.model
            else:
                self.root_model_name = False 
            self.children_ids = [(2, line_id, False) for line_id in self.children_ids.ids]
            self.report_excel_fields_ids = [(2, line_id, False) for line_id in self.report_excel_fields_ids.ids]
            self.domain = '[]'    
        else:
            if self.section:
                if self.root_model_id:
                    res = self.env['ir.model'].search([('id','=', self.root_model_id.id)],[])
                    if len(res):
                        self.root_model_name = res.model
                else:
                    self.root_model_name = False 
                self.children_ids = [(2, line_id, False) for line_id in self.children_ids.ids]
                self.report_excel_fields_ids = [(2, line_id, False) for line_id in self.report_excel_fields_ids.ids]
                self.domain = '[]'    
    @api.model
    def _list_all_models(self):
        self._cr.execute("SELECT model, name FROM ir_model ORDER BY name")
        return self._cr.fetchall() 
    @api.one
    @api.constrains('section_start','section_end')    
    def _check_start_end(self):
        _coord_re = re.compile('^[$]?([A-Z]+)[$]?(\d+)$')
        coord_string_start = self.section_start 
        match = _coord_re.match(coord_string_start)
        if not match:
            msg = '''Invalid Start Section coordinates: \"%s\",  Section: \"%s\" ! The coordinate format should be, e.g. "A5".
            '''  % (coord_string_start, self.name,) 
            raise ValidationError(msg)
        column_start, row_start = match.groups()
        row_start = int(row_start)
        if not row_start:
            msg = "There is no row 0 . Invalid Start Section coordinates: \"%s\",  Section: \"%s\" !"  % (coord_string_start, self.name,)
            raise ValidationError(msg)
        coord_string_end = self.section_end 
        match = _coord_re.match(coord_string_end)
        if not match:
            msg = '''Invalid End Section coordinates: \"%s\",  Section: \"%s\" ! The coordinate format should be, e.g. "G7".
            '''  % (coord_string_end, self.name,) 
            raise ValidationError(msg)
        column_end, row_end = match.groups()
        row_end = int(row_end)
        if not row_end:
            msg = "There is no row 0 . Invalid End Section coordinates: \"%s\",  Section: \"%s\" !"  % (coord_string_end, self.name,)
            raise ValidationError(msg)
        if row_start > row_end or CheckCell.column_index_from_string(column_start) > CheckCell.column_index_from_string(column_end):
            msg = '''Invalid START - END Section Coordinates: 
                     Start Section: \"%s\",  End Section: \"%s\",  Section Name: \"%s\" .
                     Start Section - The Upper-Left Cell of the Section. Format e.g. A5.
                     End Section - The Lower-Right cell of the Section. Format e.g. G7.
            '''  % (coord_string_start, coord_string_end, self.name,) 
            raise ValidationError(msg)
        return 
class ReportExcelFields(models.Model):
    _name = "report.excel.fields"
    _description = "Report Excel Fields"
    _order = "sequence"
    @api.model    
    def _compute_root_model(self):
        return self._context.get('root_model_id')
    @api.model    
    def _compute_root_model_name(self):
        res = self.env['ir.model'].search([('id','=', self._context.get('root_model_id'))],[])
        if len(res):
            model_name = res.model
            return model_name
    @api.model    
    def _check_root_model(self):
        res = self.env['ir.model'].search([('id','=', self._context.get('root_model_id'))],[])
        if len(res):
            return True
        else:
            if not self._context.get('section'):
                raise UserError(_('Parent Section Field is not defined. Before you can define a Report Section Fields, you must specify a Parent Section Field.'))
    @api.one
    @api.depends('field_type')
    def _compute_aggregate_ids(self):
        domain = []
        if self.field_type in ('integer', 'float', 'monetary'):
            pass
        elif self.field_type in ('date', 'datetime'):
            domain = [('code', 'in', ('max', 'min', 'count',))]
        else:
            domain = [('code', 'in', ('count',))]
        self.aggregate_ids = self.env['report.excel.aggregate'].search(domain,[]).mapped('id')
        domain = []
        if self._context.get('report_id'):
            report_id = self._context.get('report_id')
        else:
            if self.report_excel_section_id.report_id:
                report_id = self.report_excel_section_id.report_id
            else:
                report_id = 0
        if self.field_type in ('date',) and self.aggregate_id.code != 'count':
            domain = [('report_excel_id','=', report_id),('type_param','in', ('date',))]
        elif self.field_type in ('date',) and self.aggregate_id.code == 'count':
            domain = [('report_excel_id','=', report_id),('type_param','in', ('integer','float',))]
        elif self.field_type in ('datetime',) and self.aggregate_id.code != 'count':
            domain = [('report_excel_id','=', report_id),('type_param','in', ('datetime',))]
        elif self.field_type in ('datetime',) and self.aggregate_id.code == 'count':
            domain = [('report_excel_id','=', report_id),('type_param','in', ('integer','float',))]
        else:
            domain = [('report_excel_id','=', report_id),('type_param','in', ('integer','float',))]
        res_having_param = self.env['report.excel.param'].search(domain,[])
        if len(res_having_param.ids): 
            self.having_param_ids = res_having_param.mapped('id')
        else:
            self.having_param_ids = None
    sequence = fields.Integer(default=100, help="Gives the sequence of this line when displaying.")
    active = fields.Boolean(string='Active', default=True)
    show = fields.Boolean('Show', default=True)
    cell = fields.Char(string='Cell', required=True)
    report_excel_section_id = fields.Many2one('report.excel.section', string='Section', ondelete='cascade', help="Report excel Section Reference.")
    group_by = fields.Boolean('Group By', default=False)
    aggregate = fields.Selection([
        ('sum', 'SUM'),
        ('max', 'MAX'),
        ('min', 'MIN'),
        ('count', 'COUNT'),
        ('avg', 'AVG'),
    ], string='Aggregate', help="Aggregate Functions.")
    aggregate_ids = fields.Many2many('report.excel.aggregate', compute='_compute_aggregate_ids')
    aggregate_id = fields.Many2one('report.excel.aggregate', string='Aggregate', help="Aggregate Functions.")
    having_operator = fields.Selection([
        ("=", "is equal to"),
        ("!=", "is not equal to"),
        (">", "greater than"),
        ("<", "less than"),
        (">=", "greater than or equal to"),
        ("<=", "less than or equal to"),
    ], string='Having', help="The HAVING clause filters the data.")
    having_selection = fields.Selection([
        ('value', 'Value'),
        ('param', 'Report Parameter'),
    ], string='Value Type', help="Value Type for Having Clause.", default='value')
    having_param_ids = fields.Many2many('report.excel.param', compute='_compute_aggregate_ids')
    having_param_id = fields.Many2one('report.excel.param', string='Parameter', ondelete='cascade')
    having_value_type = fields.Selection([
        ('float', 'Float'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
    ], string='Having Value Type')
    having_value_float = fields.Float('Having Value')
    having_value_date = fields.Date('Having Value')
    having_value_datetime = fields.Datetime('Having Value')
    cumulative_having_field = fields.Char(compute='_compute_cumulative_having_field', string='Having')
    sort_by = fields.Selection([
        ('asc', 'ASC'),
        ('desc', 'DESC'),
    ], string='Sort', help="Order By.")
    formula = fields.Boolean('Formula', default=False)
    formulas = fields.Text('Formulas',
        default='''\u0023 Help with Python expressions \n
\u0023 The following variables can be used:
\u0023  - uid: is the current user’s database id
\u0023  - user: is the current user’s record
\u0023  - date, datetime, dateutil: useful Python libraries 
\u0023  - param(parameter_code): Report Parameter, for example  param(Parameter1_start_date)
\u0023  - cell(CELL_COORDINATE): Excel Cell of the current Section,  for example  cell(A7) \n
\u0023 Note: returned value have to be set in the variable 'result' \n
\u0023 Example of Python code:
\u0023 if (cell(A7) == "out_invoice"):
\u0023   result = cell(H7) * -1
\u0023 else:
\u0023   result = cell(H7) ''',
       help=''' The formula uses Python syntax.\nNote: returned value have to be set in the variable 'result' '''
    )
    check_root_model = fields.Boolean(string='Check Root Model', default=_check_root_model)
    root_model_id = fields.Integer(string='Report Root Model', default=_compute_root_model)
    root_model_name = fields.Selection(selection='_list_all_models', string='Report Root Model Name', default=_compute_root_model_name)
    model_field_selector = fields.Char(string='Field', default='id')
    cumulative_model_field = fields.Char(compute='_compute_cumulative_model_field', string='Field', readonly=True)
    field_type = fields.Char(string='Field Type')
    description = fields.Text('Description')
    @api.constrains('formulas')
    def _check_python_code(self):
        for f in self.sudo().filtered('formulas'):
            if f.formula:
                msg = test_python_expr(expr=f.formulas.strip(), mode="exec")
                if msg:
                    msg = 'Please check the formula in Cell "%s" !\n \n' % (f.cell,) + msg
                    raise ValidationError(msg)
    @api.model
    def _list_all_models(self):
        self._cr.execute("SELECT model, name FROM ir_model ORDER BY name")
        return self._cr.fetchall() 
    @api.one
    @api.depends('model_field_selector')
    def _compute_cumulative_model_field(self):
        name = ''
        name = self.model_field_selector if self.model_field_selector else ''
        name_split = name.split('.')
        new_name = ''
        model =  self.root_model_name    
        field_err = False
        try:
            for i in name_split:
                field = self.env[model].fields_get([i])
                display_name = field[i].get('string') 
                field_dict = field[i] 
                if 'relation' in field_dict:
                    rel = field[i].get('relation')
                else:
                    rel = ''
                new_name =  (new_name + ' --> ' + display_name + '(' + model + ')')  if (new_name != '') else (display_name + '(' + model + ')')
                model = rel
                field_type = field[i].get('type')
        except KeyError:
            new_name = ' '
            field_err = True
        if not field_err:
            self.field_type = field_type 
        self.cumulative_model_field = new_name
    @api.onchange('cumulative_model_field')
    def _onchange_aggregate_domain(self):
        self.aggregate_id = None
        self.aggregate = False
        if self.field_type in ('integer', 'float', 'monetary'):
            return {'domain': {'aggregate_id': []}}
        elif self.field_type in ('date', 'datetime'):
            return {'domain': {'aggregate_id': [('code', 'in', ('max', 'min', 'count',))]}}
        else:
            return {'domain': {'aggregate_id': [('code', 'in', ('count',))]}}
    @api.onchange('cumulative_model_field', 'aggregate_id', 'having_selection')
    def _onchange_having_param_domain(self):
        self.having_param_id = None
        if self._context.get('report_id'):
            report_id = self._context.get('report_id')
        else:
            if self.report_excel_section_id.report_id:
                report_id = self.report_excel_section_id.report_id
            else:
                report_id = 0
        if self.field_type in ('date',) and self.aggregate_id.code != 'count':
            return {'domain': {'having_param_id': [('report_excel_id','=', report_id),('type_param','in', ('date',))]}}
        if self.field_type in ('date',) and self.aggregate_id.code == 'count':
            return {'domain': {'having_param_id': [('report_excel_id','=', report_id),('type_param','in', ('integer','float',))]}}
        elif self.field_type in ('datetime',) and self.aggregate_id.code != 'count':
            return {'domain': {'having_param_id': [('report_excel_id','=', report_id),('type_param','in', ('datetime',))]}}
        elif self.field_type in ('datetime',) and self.aggregate_id.code == 'count':
            return {'domain': {'having_param_id': [('report_excel_id','=', report_id),('type_param','in', ('integer','float',))]}}
        else:
            return {'domain': {'having_param_id': [('report_excel_id','=', report_id),('type_param','in', ('integer','float'))]}}
    @api.onchange('aggregate_id')
    @api.model
    def _onchange_aggregate(self):
        if self.aggregate_id.id == False:
            self.aggregate = False
            self.having_operator = False
        else:
            self.aggregate = self.aggregate_id.code
            self.having_selection = 'value'
    @api.onchange('having_operator')
    @api.model
    def _onchange_having_operator(self):
        self.having_selection = 'value'
        self._onchange_having_selection()
    @api.onchange('aggregate_id','having_selection')
    @api.model
    def _onchange_having_selection(self):
        self.having_param_id = None
        self.having_value_float = 0.0
        self.having_value_date = None
        self.having_value_datetime = None
        if self.having_selection == None:
            self.having_selection = 'value'
    @api.onchange('cumulative_model_field', 'aggregate_id')
    def _onchange_having_value_type(self):
        self.having_value_type = False
        if self.field_type in ('date',) and self.aggregate_id.code != 'count':
            self.having_value_type = 'date'
        elif self.field_type in ('date',) and self.aggregate_id.code == 'count':
            self.having_value_type = 'float'
        elif self.field_type in ('datetime',) and self.aggregate_id.code != 'count':
            self.having_value_type = 'datetime'
        elif self.field_type in ('datetime',) and self.aggregate_id.code == 'count':
            self.having_value_type = 'float'
        else:
            self.having_value_type = 'float'
    @api.one
    @api.depends('having_operator', 'having_selection', 'having_param_id', 'having_value_type', 'having_value_float', 'having_value_date', 'having_value_datetime')
    def _compute_cumulative_having_field(self):
        new_name = ''
        if self.having_operator:
            new_name += MAP_HAVING_OPERATOR[self.having_operator] + ':'
            if self.having_selection == 'param':
                if self.having_param_id.id:
                    new_name =  new_name + '  Param(' + self.having_param_id.code + ')'
            if self.having_selection == 'value':
                if self.having_value_type == 'float':
                    new_name =  new_name + '  ' + str(self.having_value_float)
                if self.having_value_type == 'date':
                    new_name =  new_name + '  ' + str(self.having_value_date)
                if self.having_value_type == 'datetime':
                    new_name =  new_name + '  ' + str(self.having_value_datetime)
        self.cumulative_having_field = new_name
    @api.model
    @api.onchange('aggregate_id','group_by')
    def _update_aggregate_group_by(self):
        if self.aggregate_id.id != False:
            self.group_by = False
        if self.group_by != False:
            self.aggregate_id = False
    @api.model
    @api.onchange('cell')
    def _set_upper(self):
        self.cell = str(self.cell).upper() if self.cell else ''
    @api.one
    @api.constrains('cell')
    def _check_format(self):
        _coord_re = re.compile('^[$]?([A-Z]+)[$]?(\d+)$')
        coord_string = self.cell 
        match = _coord_re.match(coord_string)
        if not match:
            msg = 'Invalid cell coordinates (%s)' % coord_string
            raise ValidationError(msg)
        column, row = match.groups()
        row = int(row)
        if not row:
            msg = "There is no row 0 (%s)" % coord_string
            raise ValidationError(msg)
        return 
class ReportExcelFieldsSQL(models.Model):
    _name = "report.excel.fields.sql"
    _description = "Report Excel Fields SQL"
    _order = "cell,id"
    @api.model    
    def _compute_root_model(self):
        return self._context.get('root_model_id')
    sequence = fields.Integer(default=10, help="Gives the sequence of this line when displaying.")
    active = fields.Boolean(string='Active', default=True)
    cell = fields.Char(string='Cell', required=True)
    column_index = fields.Integer(string='SQL Column Index', required=True, help="SQL Query Column Index (0,1,2,...).")
    show = fields.Boolean('Show', default=True)
    formulas = fields.Text('Formulas')
    report_excel_section_id = fields.Many2one('report.excel.section', string='Section', ondelete='cascade', help="Report excel Section Reference.")
    root_model_id = fields.Integer(string='Report Root Model', default=_compute_root_model)
class ReportExcelAggregate(models.Model):
    _name = "report.excel.aggregate"
    code = fields.Char(string='Code')
    name = fields.Char(string='Aggregate Name')
class WizardReportMenu(models.TransientModel):
    _name = 'wizard.report.menu.create'
    menu_id = fields.Many2one('ir.ui.menu', string='Parent Menu', required=True, ondelete='cascade')
    name = fields.Char(string='Menu Name', required=True)
    @api.multi
    def menu_create(self):
        for menu in self:
            context_report1 = "{'model': 'report.excel', 'id': %d}" % (self.env.context.get('active_id'),)
            context_report2 = "{'id': %d, 'model': 'report.excel'}" % (self.env.context.get('active_id'),)
            action_id = self.env['ir.actions.act_window'].search(["&",('res_model', '=', 'report_excel_wizard'),"|",('context', '=', context_report1),('context', '=', context_report2)]).id
            if not action_id:
                report_excel_name = self.env['report.excel'].search([('id', '=', self.env.context.get('active_id'))]).name
                view_id = self.env['ir.ui.view'].search([('model', '=', 'report_excel_wizard')])
                vals = {
                    'name': report_excel_name,
                    'res_model': 'report_excel_wizard',
                    'src_model': 'report.excel',
                    'view_mode': 'form',
                    'target': 'new',
                    'view_type':"form",
                    'view_id': view_id.id,
                    'context': {
                        'model': 'report.excel',
                        'id': self.env.context.get('active_id'),
                    },
                }
                action_id = self.env['ir.actions.act_window'].create(vals)
            self.env['ir.ui.menu'].create({
                'name': menu.name,
                'parent_id': menu.menu_id.id,
                'action': 'ir.actions.act_window,%d' % (action_id,)
            })
        return {'type': 'ir.actions.act_window_close'}
class CellUtils(object):
    def __init__(self):
        self._row_finder = re.compile(r'\d+$')
        self._coord_re = re.compile('^[$]?([A-Z]+)[$]?(\d+)$')
        self._COL_STRING_CACHE = {}
        self._STRING_COL_CACHE = {}
        for i in range(1, 18279):
            col = self._get_column_letter(i)
            self._STRING_COL_CACHE[i] = col
            self._COL_STRING_CACHE[col] = i
    def coordinate_from_string(self, coord_string):
        match = self._coord_re.match(coord_string.upper())
        if not match:
            msg = 'Invalid cell coordinates (%s)' % coord_string
            raise ValueError(msg)
        column, row = match.groups()
        row = int(row)
        if not row:
            msg = "There is no row 0 (%s)" % coord_string
            raise ValueError(msg)
        return (column, row)
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
    def get_column_letter(self, idx,):
        try:
            return self._STRING_COL_CACHE[idx]
        except KeyError:
            raise ValueError("Invalid column index {0}".format(idx))
    def column_index_from_string(self, str_col):
        try:
            return self._COL_STRING_CACHE[str_col.upper()]
        except KeyError:
            raise ValueError("{0} is not a valid column name".format(str_col))
    def cell_from_index(self, col_ind, row_ind):
        col_letter = self.get_column_letter(col_ind) 
        return ''.join([col_letter,str(row_ind)])
CheckCell = CellUtils()
