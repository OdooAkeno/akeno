# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2018 GRIMMETTE,LLC <info@grimmette.com>

import base64
from datetime import date, datetime, timedelta
import time
import dateutil
from itertools import chain, groupby
from operator import itemgetter, attrgetter, methodcaller
import json
import logging
import os
import re
import shutil
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED, BadZipfile
from odoo.osv import expression
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo.tools import float_round, float_is_zero, ustr
from ..models.xlsx import XLSXEdit
_logger = logging.getLogger(__name__)
SUPPORTED_FORMATS = ('.xlsx', '.xlsm')
MAP_PARAM_TYPE_BLANK = {
    'char':      ['not in', [0]],
    'integer':   [False, 0],
    'float':     [False, 0.0],
    'many2one':  ['not in', [0]],
    'many2many': ['not in', [0]],
    'date':      ['not in', [0]],
    'datetime':  ['not in', [0]],
    'boolean':   [False, False],
}
MAP_x2M_OPERATOR = {
    '=':  'in',
    '!=':  'not in',
}
MAP_FIELD_TYPE_BLANK = {
    'integer':   -100000000000,
    'float':     -100000000000.00,
    'monetary':  -100000000000.00,
    'date':      date(2000, 1, 1),
    'datetime':  datetime(2000, 1, 1),
}
def dc(obj): 
    if isinstance(obj, dict):
        d = obj.copy() 
        for k,v in list(d.items()):
            d[k] = dc(v)
    elif isinstance(obj, (list)):
        d = obj[:] 
        i = len(d)
        while i:
            i -= 1
            d[i] = dc(d[i])
    elif isinstance(obj, (tuple)):
        d = obj[:] 
    else:
        d = obj 
    return d
class ReportExcelGen(models.TransientModel):
    _name = 'report_excel_gen'
    def _validate_archive(self, file, filename):
        is_file_like = hasattr(filename, 'read')
        if not is_file_like and os.path.isfile(filename):
            file_format = os.path.splitext(filename)[-1].lower()
            if file_format not in SUPPORTED_FORMATS:
                if file_format == '.xls':
                    msg = ('Does not support the old .xls file format, '
                           'please convert it to .xlsx or .xlsm file format.')
                elif file_format == '.xlsb':
                    msg = ('Does not support binary format .xlsb, '
                           'please convert this file to .xlsx or .xlsm format.')
                else:
                    msg = ('Does not support %s file format, '
                           'please check you can open '
                           'it with Excel first. '
                           'Supported formats are: %s') % (file_format,
                                                           ','.join(SUPPORTED_FORMATS))
                raise UserError(msg)
        if is_file_like:
            if getattr(file, 'encoding', None) is not None:
                raise IOError("File-object must be opened in binary mode")
        try:
            archive = ZipFile(file, 'r', ZIP_DEFLATED)
            archive.testzip()
            archive.close() 
            arc_check = True
        except BadZipfile:
            msg = ('Does not support the file format, '
                   'please use .xlsx file format.')
            arc_check = False
        return arc_check
    @api.model
    @api.returns('ir.attachment', lambda value: value.id)
    def _get_template(self, template_id):
        return self.env['ir.attachment'].search([('res_model', '=', 'report.excel'), ('id', '=', template_id)])
    def _get_conf(self, conf_id):
        return self.env['report.excel'].browse(conf_id)
    def copyFile(self, src, dest):
        try:
            shutil.copy(src, dest)
        except shutil.Error as e:
            _logger.info('Error: %s' % e)
        except IOError as e:
            _logger.info('Error: %s' % e.strerror)
    @api.multi    
    def create_xls(self, datas=None, cellutil=None):
        datas = datas if datas is not None else {}
        tmp_dir = tempfile.gettempdir()
        res_conf = {}
        res_conf = self._get_conf(datas['form']['report_conf_id']) or {}
        if not res_conf:
            msg = ('The Report has been Deleted or Archived.')
            raise UserError(msg)            
        chain_ids_tpl = tuple(datas['ids'])
        records = self.env[datas['active_model']].browse(datas['ids'][0]) if len(datas['ids']) else ()
        for record in records:
            try:
                f_name = safe_eval(res_conf['out_file_name'],{'obj': record, 'time': time, 'datetime': datetime})
                out_file_name = safe_eval("datetime.now().strftime(f_name)",{'obj': record, 'time': time, 'datetime': datetime, 'f_name': f_name})
                break
            except:
                _logger.info("Error or Old 'Output File Name' Expression Definition Syntax: %s  !", res_conf['out_file_name'])
                out_file_name = datetime.now().strftime(res_conf['out_file_name'])
                break            
        else:
            out_file_name = datetime.now().strftime(res_conf['out_file_name'])
        out_file_name = re.sub(r'[\'\"\+\.\,\+]','', out_file_name)
        out_file_name = re.sub(r'[\/' ']','_', out_file_name)
        out_file_name = out_file_name +'.xlsx'            
        template_xlsx = 0    
        if res_conf:
            template_xlsx = res_conf['template_name_id']
        tmpfile_wfd, tmpfile_wpath = tempfile.mkstemp(suffix='.xlsx', prefix='xslx.tmpl.tmp.')
        if template_xlsx:
            template = {} 
            template = self._get_template(template_xlsx.id)
            fname = template['datas_fname']
            store_fname = template['store_fname']
            template_fp = template._full_path(store_fname)
            self.copyFile(template_fp,tmpfile_wpath)
        else:
            base_template_fp = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'Book1.xlsx')
            self.copyFile(base_template_fp,tmpfile_wpath)
        user = self.env['res.users'].browse(self.env.uid)
        company_name=user.company_id.display_name
        xlsx_template = XLSXEdit(tmpfile_wpath, cellutil)
        Models_Env = ModelsEnv()
        Fields_Env = FieldsEnv()        
        Rels = Relations()        
        conf_data = {'conf':{}, 'data':{}}
        if template_xlsx:
            conf_data['conf']['sheet_reference'] =  res_conf.sheet_reference
        else:
            conf_data['conf']['sheet_reference'] =  'Sheet1'
        if not xlsx_template.check_conf(conf_data['conf']):
            raise UserError(_('Template configuration Error. \nInvalid Sheet Name: \"%s\".\n'\
                              'Please check the Sheet Name in the template configuration, It must match the Name of the Sheet in the EXCEL Workbook.') % (conf_data['conf']['sheet_reference'],))
        conf_data['conf']['show_level'] =  res_conf.show_level
        conf_data['conf']['show_autofilter'] =  res_conf.show_autofilter
        conf_data['conf']['root_model_id'] =  res_conf.root_model_id.id
        conf_data['conf']['root_model_name'] =  res_conf.root_model_id.model
        conf_data['conf']['report_params'] =  {}
        for i in res_conf.report_excel_param_ids:
            if i['wizard_param_ir_model_field_id']['name'] in datas['form'].get('data'):
                conf_data['conf']['report_params'][i['code']]  = [
                    i['id'],
                    i['code'],
                    i['type_param'],
                    i['param_ir_model_id']['id'],
                    datas['form'].get('data').get(i['wizard_param_ir_model_field_id']['name'])]
            else:
                conf_data['conf']['report_params'][i['code']]  = [i['id'],i['code'],i['type_param'],i['param_ir_model_id']['id'],False] 
        conf_data['conf']['section'] =  {}
        for i in res_conf.report_excel_section_ids:
            conf_data['conf']['section'][i['id']] = self._get_section_conf(i['id'], conf_data['conf']['report_params'], xlsx_template)
        conf_data['conf']['data_lines'] =  {}
        conf_data['conf']['data_lines']['row_min'] = 1000000       
        conf_data['conf']['data_lines']['row_max'] = 0            
        conf_data['conf']['data_lines']['col_min'] = 1000000       
        conf_data['conf']['data_lines']['col_max'] = 0            
        conf_data['conf']['data_lines']['section_boundaries'] = {}
        conf_data['conf']['data_lines']['section_max'] = ()
        conf_data['conf']['data_lines']['matrix_cell_idx'] = {}            
        for k, v in list(conf_data['conf']['section'].items()):
            self._get_section_ids(k, conf_data['conf'])
        for s_id in conf_data['conf']['section']:
            conf_data['data'][s_id] =  self._get_section_data(s_id, conf_data['conf'], chain_ids_tpl, xlsx_template, [], None, {}, (), Models_Env, Fields_Env)
        conf_data_out = dc(conf_data)
        for s_id in conf_data_out['data']:
            self._post_processing_data(s_id, conf_data_out['conf'], conf_data_out['data'])
        root_sections = []
        for k, v in list(conf_data_out['conf']['section'].items()):
            root_sections.append((k, v['section_start'], v['section_end'],))
            conf_data_out['conf']['data_lines']['row_min'] = self._get_conf_coordinate(xlsx_template, v['section_start'])[2] if self._get_conf_coordinate(xlsx_template, v['section_start'])[2] < conf_data_out['conf']['data_lines']['row_min'] else conf_data_out['conf']['data_lines']['row_min']  
            conf_data_out['conf']['data_lines']['row_max'] = self._get_conf_coordinate(xlsx_template, v['section_end'])[2] if self._get_conf_coordinate(xlsx_template, v['section_end'])[2] > conf_data_out['conf']['data_lines']['row_max'] else conf_data_out['conf']['data_lines']['row_max']
            conf_data_out['conf']['data_lines']['col_min'] = self._get_conf_coordinate(xlsx_template, v['section_start'])[1] if self._get_conf_coordinate(xlsx_template, v['section_start'])[1] < conf_data_out['conf']['data_lines']['col_min'] else conf_data_out['conf']['data_lines']['col_min']  
            conf_data_out['conf']['data_lines']['col_max'] = self._get_conf_coordinate(xlsx_template, v['section_end'])[1] if self._get_conf_coordinate(xlsx_template, v['section_end'])[1] > conf_data_out['conf']['data_lines']['col_max'] else conf_data_out['conf']['data_lines']['col_max']
        for k, v in list(conf_data_out['conf']['data_lines']['section_boundaries'].items()):
            conf_data_out['conf']['data_lines']['section_boundaries'][k]['min'] =  self._get_conf_coordinate(xlsx_template, conf_data_out['conf']['data_lines']['section_boundaries'][k]['min']) 
            conf_data_out['conf']['data_lines']['section_boundaries'][k]['max'] =  self._get_conf_coordinate(xlsx_template, conf_data_out['conf']['data_lines']['section_boundaries'][k]['max']) 
            conf_data_out['conf']['data_lines']['section_boundaries'][k]['max'].append(conf_data_out['conf']['data_lines']['section_boundaries'][k]['max'][2]) 
            conf_data_out['conf']['data_lines']['section_max'] += (conf_data_out['conf']['data_lines']['section_boundaries'][k]['max'][0],) 
        conf_data_out['conf']['data_lines']['section_max'] = tuple(set(conf_data_out['conf']['data_lines']['section_max']))
        if len(root_sections): 
            root_sections_tmp = []
            for n in root_sections:
                root_sections_tmp.append((n[0], tuple(self._get_conf_coordinate(xlsx_template, n[1])), tuple(self._get_conf_coordinate(xlsx_template, n[2])),))
            f_get_item_1 = itemgetter(1)
            f_get_item_2 = itemgetter(2)
            root_sections_sorted = sorted(root_sections_tmp, key=lambda x: (f_get_item_2(f_get_item_1(x)),f_get_item_1(f_get_item_1(x)),))
            xlsx_conf = xlsx_template.write_conf(conf_data_out['conf'])            
            for i in root_sections_sorted:
                self._get_order(i[0], conf_data_out['conf'], xlsx_template)
            res_data = []
            for r in range(conf_data_out['conf']['data_lines']['row_min']):
                res_data.append([])
                for c in range(conf_data_out['conf']['data_lines']['col_max']+1):
                    if c != 0 and r != 0:
                        res_data[r].append([[None, xlsx_template.get_column_letter(c), c, r, r], 
                                            {'mergecell': False, 'style': '0', 'section_ids': (), 'present': False, 'formula': False, 'pack': False, 'value': None}])
                    else:
                        if c != 0:
                            res_data[r].append([[None, xlsx_template.get_column_letter(c), c, r, r], {'mergecell': False, 'style': '0', 'section_ids': (), 'present': False, 'formula': False, 'pack': False, 'value': None}])
                        else:
                            res_data[r].append([[None, None, c, r, r], {'mergecell': False, 'style': '0', 'section_ids': (), 'present': False, 'formula': False, 'pack': False, 'value': None}])
            row_idx = 0
            for r in xlsx_conf['matrix_template']:
                self._ch_idx(r[1], res_data)
                cell_idx = 0                 
                for cell in r[2]:
                    res_data[r[1]][cell[0][2]] = dc(cell)
                    conf_data_out['conf']['data_lines']['matrix_cell_idx'][cell[0][0]] = (row_idx, 2, cell_idx,)  
                    cell_idx += 1
                row_idx += 1 
            for i in root_sections_sorted:
                self._get_start_section(i[0], conf_data_out, xlsx_template, Rels)
                self._get_start_cell(i[0], conf_data_out, xlsx_template, Rels)
            for i in root_sections_sorted:
                self._preparing_data(i[0], conf_data_out, xlsx_template, res_data)
            for col in res_data:
                for cell in col:
                    if cell[0][0] is not None and cell[1]['value'] is not None:
                        xlsx_template.write(conf_data_out['conf']['sheet_reference'], xlsx_template.cell_from_coordinate(cell[0][1], cell[0][3]) , cell[1]['value'], cell_ext=cell)    
            xlsx_template.update_conf(conf_data_out['conf'], False, res_data)
            xlsx_template.shift_coordinate_row(conf_data_out['conf']['sheet_reference'], xlsx_conf['row_data_max'] + 1, len(res_data) - xlsx_conf['row_data_max'] -1)
        out_tmpfile_wpath = ''.join([xlsx_template._zip_folder, '.xlsx'])
        with open(out_tmpfile_wpath, 'wb') as zip_file:
            zip_file.write(xlsx_template.get_content())
        zipOb = ZipFile(out_tmpfile_wpath)
        zipOb.testzip()
        zipOb.close() 
        with open(out_tmpfile_wpath,'rb') as m:
            data_attach = {
                'name': res_conf.name,
                'name': out_file_name,
                'datas': base64.b64encode(m.read()),
                'type': "binary",
                'datas_fname': out_file_name,
                'res_model': 'report.excel',
                'res_id': 0,
            }
            try:
                new_attach = self.env['ir.attachment'].create(data_attach)
            except AccessError:
                _logger.info("Cannot save %r as attachment", out_file_name)
            else:
                _logger.info('The document %s is now saved in the database', out_file_name)
        new_attach_fpath = ''
        new_attach_fname = ''
        if new_attach: 
            new_attach_fname = new_attach['datas_fname']
            store_fname = new_attach['store_fname']
            new_attach_fpath = new_attach._full_path(store_fname)
        self._validate_archive(new_attach_fpath, new_attach_fname)
        if datas['send_by_email']:
            template_id = res_conf.email_template_id.id
            try:
                compose_form_id = self.env['ir.model.data'].get_object_reference('mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False
            lang = self.env.context.get('lang')
            template = template_id and self.env['mail.template'].browse(template_id)
            if template and template.lang and len(datas['ids']):
                lang = template._render_template(template.lang, datas['active_model'], datas['ids'][0])
            ctx = {
                'default_model': res_conf.root_model_id.model,
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',
                'default_attachment_ids': (new_attach.id,),
                'force_email': True
            }
            ctx['default_res_id'] = datas['ids'][0] if len(datas['ids']) else 0 
            return {
                'name': _('Compose Email'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form_id, 'form')],
                'view_id': compose_form_id,
                'target': 'new',
                'context': ctx,
            }
        else:
            file_obj = {
                'type': 'ir.actions.act_url',
                'url': '/report_excel?id=%s' % (new_attach.id,), 
                'target': 'self',
            }
            return file_obj
    def _get_section_conf(self, section_id, params=None, xlsx_template=None, chain_group=None):
        conf_section = {}
        section = self.env['report.excel.section'].search_read([('id','=', section_id)],[])[0]
        chain_group_ext = False
        fields = self.env['report.excel.fields'].search_read([('id', 'in', section['report_excel_fields_ids'])],[])
        for f in fields:
            if f['show']:
                chain_group_ext = f['show'] 
        if chain_group == None:
            chain_group = (chain_group_ext,)
        else:
            chain_group_lst = list(chain_group)
            chain_group_lst.append(chain_group_ext)
            chain_group = tuple(chain_group_lst)
        conf_section  = {
            'id': section['id'],
            'name': section['name'],
            'parent_id': section['parent_id'],
            'root_model_id': section['root_model_id'][0],     
            'root_model_name': section['root_model_name'],
            'root_model_related_field_id': section['root_model_related_field_id'],
            'children_ids': {d['id']:d for d in ([self._get_section_conf(p, params, xlsx_template, chain_group) for p in section['children_ids']] if len(section['children_ids']) else section['children_ids'])},
            'section_start': section['section_start'],
            'section_end': section['section_end'],
            'level': section['level'],
            'domain': self._get_domain(section['domain'], params),
            'report_excel_fields_ids': {d[0][0]:d for d in ([self._get_fields_conf(p, params, xlsx_template) for p in section['report_excel_fields_ids']] if len(section['report_excel_fields_ids']) else section['report_excel_fields_ids'])},
            'sql_bool': section['sql_bool'],
            'report_excel_fields_sql_ids': section['report_excel_fields_sql_ids'],
            'sql_statement': section['sql_statement'],
            'type_data': section['type_data'],
            'chain_group': chain_group,
            'cell_section_order': (),
            }
        return conf_section
    def _get_domain(self,domain, params):
        if isinstance(domain, (list, tuple)):
            return domain        
        domain_arr = []
        if domain != '[]' and domain != False:
            domain_arr = safe_eval(ustr(domain))
            for k, v in list(params.items()):
                p = ''.join(['param(',v[1],')'])
                for s in domain_arr:
                    if isinstance(s,list):
                        if p == s[2]:
                            if v[4]: 
                                if isinstance(v[4],list):
                                    s[2] = tuple(v[4]) 
                                else:
                                    s[2] = v[4] 
                                if v[2] in ('one2many','many2many'):
                                    if s[1] in ('=','!='):
                                        s[1] = MAP_x2M_OPERATOR[s[1]]
                            else:
                                if MAP_PARAM_TYPE_BLANK[v[2]][0]:
                                    s[0] = 'id'
                                    s[1] = MAP_PARAM_TYPE_BLANK[v[2]][0]
                                s[2] = MAP_PARAM_TYPE_BLANK[v[2]][1]
        return domain_arr
    def _get_fields_conf(self, field_id, params=None, xlsx_template=None):
        conf_field = []
        fields = self.env['report.excel.fields'].browse(field_id)
        for n in fields:
            having_value = None
            if (n.having_operator != False):
                if (n.having_selection == 'param'):
                    res_param = self.env['report.excel.param'].browse(n.having_param_id.id)
                    for k,v in list(params.items()):
                        if res_param.id == v[0]: 
                            if v[4]:  
                                if res_param.type_param ==  'date':
                                    having_value = v[4]
                                elif res_param.type_param ==  'datetime':
                                    having_value = v[4]
                                else:
                                    having_value = float(v[4])
                            else:
                                if res_param.type_param  in ('integer', 'float',):
                                    having_value = 0.0
                else: 
                    if n.having_value_type ==  'float':
                        having_value = n.having_value_float
                    if n.having_value_type ==  'date':
                        having_value = n.having_value_date
                    if n.having_value_type ==  'datetime':
                        having_value = n.having_value_datetime
            conf_field = [self._get_conf_coordinate(xlsx_template, n.cell), 
                          n.id, 
                          n.model_field_selector,
                          n.report_excel_section_id.id,    
                          {
                          'group_by': n.group_by,
                          'aggregate': n.aggregate,
                          'having_operator': n.having_operator,
                          'having_value': having_value,
                          'sort_by': n.sort_by,
                          'formula': n.formula,
                          'formulas': self._get_formulas(n.formulas, params) if n.formula else n.formulas , 
                          'show': n.show,
                          'sequence': n.sequence,
                          'field_type': n.field_type,
                          'cell_start': {},
                          }]
        return conf_field
    def _get_formulas(self, formula, params):
        if formula:
            f_split = formula.split("\n")
            for i, f in enumerate(f_split):
                if f.find('#') > -1:
                    f_split[i] = f[:f.find('#')]
            for i, f in enumerate(f_split):            
                while f.find('param(') > -1:
                    ist = f.find('param(')
                    ie = f.find(')', ist+6)
                    pcode = f[ist+6:ie].strip()
                    param = params.get(pcode)
                    pv =  '\"' + '' + '\"'
                    if param:
                        if param[2] in ('char',):
                            pv = '\"'+ param[4] + '\"'  if param[4] else '\"' + '' + '\"'
                        elif param[2] in ('boolean',):
                            pv = 'True' if param[4] else 'False'
                        elif param[2] in ('date',):
                            pv = 'datetime.strptime(\"'+ param[4] + '\", \"%Y-%m-%d\").date()'  if param[4] else '\"\"'
                        elif param[2] in ('datetime',):
                            pv = 'datetime.strptime(\"'+ param[4] + '\", \"%Y-%m-%d %H:%M:%S\")'  if param[4] else '\"\"'
                        elif param[2] in ('many2one',):
                            if param[4]:
                                comodel = self.env['ir.model'].browse(param[3]).model
                                pv = '\"'+ self.env[comodel].browse(param[4]).display_name + '\"'
                            else:
                                pv = '\"' + '' + '\"'    
                        elif param[2] in ('many2many',):
                            if param[4]:
                                pv = '()'
                                comodel = self.env['ir.model'].browse(param[3]).model
                                res_model = self.env[comodel].browse(param[4])
                                for res in res_model:
                                    pv = pv[:-1] + '\"' + res.display_name + '\"' + ',' + pv[-1:]
                            else:
                                pv =  '()'    
                        else:
                            pv = param[4] if param[4] else 0
                        f_split[i] = f = f[:ist] + str(pv) + f[ie+1:]
                    else:
                        if pcode not in ('parameter_code', 'Parameter1_start_date',):    
                            msg = ('''Parameter code  %s  not found!
                                   Please check the Parameter Code in the formula.
                                   If you want to access report parameters, use the syntax: param(parameter code), for example  param(Parameter1_start_date)'''
                                   ) % (pcode,)
                            raise UserError(msg)
        f_n = ''
        for s in f_split:
            if len(s):
                f_n = f_n + s + "\n"
        return f_n
    def _get_section_data(self, section_id, conf=None, active_ids=(), xlsx_template=None, order=[], parent_data_line_id=None, res={}, chain_ids=(), Models_Env={}, Fields_Env={}):
        conf_active = self._get_active_conf(section_id, conf, order)
        domain_ext = conf_active['domain']
        if len(active_ids):
            domain_ext = expression.AND([conf_active['domain'], [('id', 'in', active_ids)]])            
        child_related_field_name = []
        for child_section_id in conf_active['children_ids']:
            child_conf = self._get_active_conf(child_section_id, conf, order)
            child_related_field_name.append(self.env['ir.model.fields'].browse(child_conf['root_model_related_field_id'][0]).name)
        res_root_lines = []
        res_root_lines_test = self.env[conf_active['root_model_name']].search(domain_ext)
        for record in res_root_lines_test:
            rec_dict_tmp = {}
            field_id = record._fields.get('id')
            rec_dict_tmp['id'] = field_id.convert_to_read(record[field_id.name], record, use_name_get=True)
            for k in child_related_field_name:
                field = record._fields.get(k)
                try:
                    rec_dict_tmp[k] = field.convert_to_read(record[field.name], record, use_name_get=True)
                except:
                    rec_dict_tmp[k] = False 
            res_root_lines.append(rec_dict_tmp)
        data = []
        if 'children_ids' not in res:
            res['children_ids'] = {}
        if 'data' not in res:
            res['data'] = []
        for data_line in res_root_lines:
            chain_ids_lst = list(chain_ids)
            chain_ids_lst.append(data_line['id'])
            chain_ids_tpl = tuple(chain_ids_lst)
            data.append([[parent_data_line_id], (chain_ids_tpl,), [data_line['id']], self._get_field_data(data_line, conf_active, xlsx_template, Models_Env, Fields_Env)])
            for child_section_id in conf_active['children_ids']:
                child_conf = self._get_active_conf(child_section_id, conf, order)
                root_field_name = self._get_model(Models_Env, 'ir.model.fields')[child_conf['root_model_related_field_id'][0]].name
                root_active_ids = []
                if type(data_line[root_field_name]) == list:
                    for n in data_line[root_field_name]:
                        root_active_ids.append(n)
                if type(data_line[root_field_name]) == tuple:
                    root_active_ids.append(data_line[root_field_name][0])
                if type(data_line[root_field_name]) == bool:
                    root_active_ids.append(0)
                if not len(root_active_ids):
                    root_active_ids.append(0)
                root_active_ids_tpl = tuple(root_active_ids) 
                if child_section_id not in res['children_ids']:
                    res['children_ids'][child_section_id] = {}
                self._get_section_data(child_section_id, conf, root_active_ids_tpl, xlsx_template, order, data_line['id'], res['children_ids'][child_section_id], chain_ids_tpl, Models_Env, Fields_Env)
        for d in data:    
            res['data'].append(d)         
        return res
    def _get_field_data(self, res, conf, xlsx_template, Models_Env, Fields_Env):
        val = {}
        for k, v in list(conf['report_excel_fields_ids'].items()):
            field_split = tuple(v[2].split("."))
            val[k] = [self._get_conf_coordinate(xlsx_template, k), self._get_data(res['id'], conf['root_model_name'], field_split, Models_Env, Fields_Env)]
        return val
    def _get_data(self, id, model, field_split, Models_Env, Fields_Env):
        res_test = self._get_model(Models_Env, model).get(id)
        if res_test is None:
            return ((None,'',),)
        else:
            res = {}
            field1 = res_test._fields.get("id")
            try:
                res["id"] = field1.convert_to_read(res_test[field1.name], res_test, use_name_get=True)
            except:
                res["id"] = False
            field2 = res_test._fields.get(field_split[0])
            try:
                res[field_split[0]] = field2.convert_to_read(res_test[field2.name], res_test, use_name_get=True)
            except:
                res[field_split[0]] = False
        try:
            field = self._get_field(Fields_Env, model, field_split[0])
        except:
            _logger.info("Error! Field '%s' not found in the database!", field_split[0])
            msg = ('''Field '%s' not found in the database ! \n
                    Perhaps the field has been deleted. 
                    Please check the report configuration!'''
                    ) % (field_split[0],)
            raise UserError(msg)
        if len(field_split) > 1:
            field_split_ext = field_split[1:]            
            if field['type'] == 'many2one':
                if res[field_split[0]]:  
                    res_value = self._get_data(res[field_split[0]][0], field['relation'], field_split_ext, Models_Env, Fields_Env)
                else:
                    res_value = ((None,'',),)
            else:
                if len(res[field_split[0]]):
                    res_value = ()
                    for p in res[field_split[0]]:
                        res_value = res_value + self._get_data(p, field['relation'], field_split_ext, Models_Env, Fields_Env)
                else:
                    res_value = ((None,'',),)
            return res_value
        else:
            if field['type'] == 'many2one':
                if res[field_split[0]]:  
                    res_value = (res[field_split[0]],)
                else:
                    res_value = ((None,'',),)
            elif field['type'] == 'one2many':
                res_value = self._get_x2many(model, field['relation'], field_split[0], res['id'], Models_Env)
            elif field['type'] == 'many2many':
                res_value = self._get_x2many(model, field['relation'], field_split[0], res['id'], Models_Env)
            elif field['type'] == 'boolean':
                if res[field_split[0]]:
                    res_value = ((None,'True',),)
                else:
                    res_value = ((None,'',),)
            elif field['type'] in ['date','datetime']:
                if res[field_split[0]]:
                    res_value = ((None, res[field_split[0]],),)
                else:
                    res_value = ((None,'',),)
            elif field['type'] == 'selection':
                    if res[field_split[0]] and res[field_split[0]] != 'None':
                        for s in field['selection']:
                            if s[0] ==  res[field_split[0]]:
                                res_value = ((None, s[1]),)
                    else:
                        res_value = ((None,'',),)
            else:
                if field_split[0] in res:
                    res_value = ((None, res[field_split[0]],),)
                    if type(res_value[0][1]) == bool:
                        res_value = ((None,'',),)
                else:
                    res_value = ((None,'',),)
            return res_value
    def _get_section_ids(self, section_id, conf=None, section_chain_ids=None):
        conf_active = self._get_active_conf(section_id, conf)        
        if section_chain_ids is None:
            section_chain_ids = ()
        section_chain_ids += (conf_active['id'],)
        conf['data_lines']['section_boundaries'][section_id] = {
                                                                'min': conf_active['section_start'], 
                                                                'max': conf_active['section_end'],
                                                                'section_chain_ids': section_chain_ids
                                                                }
        for k, v in list(conf_active['children_ids'].items()):
            self._get_section_ids(k, conf, section_chain_ids)        
    def _post_processing_data(self, section_id, conf=None, data=None, parent_chain_ids=None, having_remove_ids=None):
        conf_active = self._get_active_conf(section_id, conf)
        data_active = self._get_active_data(section_id, data, conf)
        if having_remove_ids is not None and len(having_remove_ids):
            data_temp = []
            new_having_remove_ids = ()
            for rec in data_active['data']:
                if rec[0][0] not in having_remove_ids:
                    data_temp.append(rec)
                else:
                    new_having_remove_ids += tuple(rec[2])
            data_active['data'] = dc(data_temp)
            having_remove_ids = new_having_remove_ids
        for k, v in list(sorted(conf_active['report_excel_fields_ids'].items(), key = lambda x : x[1][4]['sequence'])):
            if v[4]['formula']:
                for dl in data_active['data']:
                    res_value = ()
                    for cell_val in dl[3][k][1]:
                        f = v[4]['formulas']
                        while f.find('cell(') > -1:
                            i = f.find('cell(')
                            ie = f.find(')', i+5)
                            ccode = f[i+5:ie].strip()
                            cell = dl[3].get(ccode)
                            rv =  '\"' + '' + '\"'
                            if cell != None:
                                ref_val = dl[3][ccode][1][0][1] if not k == ccode else cell_val[1]
                                if type(ref_val) in (str,):
                                    rv = '\"\"\"'+ ref_val + '\"\"\"'  if ref_val else '\"' + '' + '\"'
                                elif type(ref_val) in (bool,):
                                    rv = 'True' if ref_val else 'False'
                                elif type(ref_val) in (date,):
                                    rv_str = '\"'+ datetime.strftime(ref_val, "%Y-%m-%d") + '\"'  if ref_val else '\"' + '' + '\"'
                                    rv = 'datetime.strptime('+ rv_str + ', \"%Y-%m-%d\").date()' if rv_str != '""' else rv_str
                                elif type(ref_val) in (datetime,):
                                    rv_str = '\"'+ datetime.strftime(ref_val, "%Y-%m-%d %H:%M:%S") + '\"'  if ref_val else '\"' + '' + '\"'
                                    rv = 'datetime.strptime('+ rv_str + ', \"%Y-%m-%d %H:%M:%S\")' if rv_str != '""' else rv_str
                                else:
                                    rv = ref_val
                                f = f[:i] + str(rv) + f[ie+1:]
                            else:
                                msg = ('''Cell  "%s"  not found in Section "%s" ! \n
                                       Please check the formula in Cell "%s":\n "%s" . \n
                                       If you want to access section cells, use the syntax: cell(ADDRESS), for example  cell(A1)'''
                                       ) % (ccode, conf_active['name'], k, v[4]['formulas'],)
                                raise UserError(msg)
                        try:
                            globaldict = {
                                'datetime': datetime,
                                'date': date,
                                'dateutil': dateutil,
                                'uid': self.env.uid,
                                'user': self.env.user,
                                'json': json,
                            }                            
                            localdict = {'result': ''}
                            safe_eval(f, globals_dict = globaldict, locals_dict = localdict, mode="exec", nocopy=True) 
                            n_val =  'result' in localdict and localdict['result'] or ''
                            if type(n_val) not in (int, float, bool, date, datetime, str,):
                                n_val = str(n_val)
                                if type(n_val) not in (int, float, bool, date, datetime, str,):
                                    n_val = 'ERROR IN FORMULA'
                            res_value += ((cell_val[0], n_val),)
                        except ValueError as e:
                            msg = ('''Cell "%s" \n
                                    ERROR IN FORMULA: \n%s \n
                                    ERROR: \n%s \n
                                    PLEASE CHECK THE PYTHON EXPRESSIONS! 
                                    '''
                                   ) % (k, f, e)
                            raise UserError(msg)
                    dl[3][k][1] = res_value 
        group_by = []
        for k, v in list(conf_active['report_excel_fields_ids'].items()):
            if v[4]['group_by']:
                group_by.append((k, v[4]['sequence'], v[4]['field_type']))
        chain_group_ind = -1
        if len(conf_active['chain_group']) > 1:
            n = 0
            for i in conf_active['chain_group']:  
                if (i == True and n != len(conf_active['chain_group'])-1):
                    chain_group_ind = n
                n += 1
        group_by_sorted = sorted(group_by, key=itemgetter(1))  
        group_by_cmp_tpl = tuple(map(itemgetter(0), group_by_sorted))
        def get_vals(c, f, p):
            f_get_item_1 = itemgetter(1)
            f_get_item_3 = itemgetter(3)
            if len(f):
                f_get_items = itemgetter(*f)
                if c != -1 and (lambda *args: len(f_get_item_1(*args)) > 1):
                    return lambda *args: str([x for x in [x for x in p if f_get_item_1(*args)[0][:c+1] in x]] +  [x for x in f_get_items(f_get_item_3(*args))])
                else:
                    return lambda *args:  str([x for x in f_get_items(f_get_item_3(*args))])
            else:
                if c != -1 and (lambda *args: len(f_get_item_1(*args)) > 1):
                    return lambda *args: str([x for x in [x for x in p if f_get_item_1(*args)[0][:c+1] in x]])
                else:
                    return lambda *args: '()'
        get_vals_f = get_vals(chain_group_ind, group_by_cmp_tpl, parent_chain_ids)
        data_sorted = sorted(data_active['data'], key=get_vals_f)
        groups = []
        for k, g in groupby(data_sorted, get_vals_f):
            groups.append(list(g))      
        sort_by_group = []
        sort_by_group_key = []
        for k, v in list(conf_active['report_excel_fields_ids'].items()):
            if v[4]['sort_by'] and v[0][0] not in group_by_cmp_tpl:
                sort_by_group.append((k, v[4]['sequence'], v[4]['sort_by'],))
                sort_by_group_key.append(k)
        if len(sort_by_group):
            f_get_item_1 = itemgetter(1)
            sort_by_group_sorted = tuple(sorted(sort_by_group, key=f_get_item_1, reverse=True))  
            def get_val_sort_group(f, ft):
                f_get_item_1 = itemgetter(1)
                f_get_item_3 = itemgetter(3)
                f_get_item_f = itemgetter(f)
                def permutation(t,ft):
                    new_t = []
                    for n in t:
                        n0 = 0 if n[0] is None else n[0]
                        n1 = MAP_FIELD_TYPE_BLANK[ft] if n[1] == '' and ft in ('integer', 'float', 'monetary', 'date', 'datetime',) else n[1]
                        new_t.append((n1,n0,))
                    return tuple(new_t)
                return lambda *args: permutation(f_get_item_1(f_get_item_f(f_get_item_3(*args))), ft)
            for s in sort_by_group_sorted:
                get_val_sort_group_f = get_val_sort_group(s[0], conf_active['report_excel_fields_ids'][s[0]][4]['field_type'])
                if s[2] == 'asc':
                    reverse = False 
                else:
                    reverse = True 
                for group in groups:
                    try:
                        if len(group) > 1:
                            group.sort(key=get_val_sort_group_f, reverse=reverse)
                    except TypeError as e:
                        msg = ('''ERROR DURING SORTING CELL "%s" !\n
                                PLEASE CHECK THE PYTHON EXPRESSIONS IN FORMULA: \n%s \n
                                ERROR: \n%s \n
                                Sorting can not be performed on different data types!
                                '''
                               ) % (s[0], f, e)
                        raise UserError(msg)                
        data_active_res = []
        for g in groups:
            group_res = []
            for i in g:
                if not len(group_by):
                    if  len(conf_active['report_excel_fields_ids']):
                        group_res.append(dc(i))
                    else:
                        if len(group_res)==0: 
                            group_res.append(dc(i))
                        else:
                            group_res[0][0].append(i[0][0]) 
                            group_res[0][1] = group_res[0][1] + i[1]
                            group_res[0][2].append(i[2][0]) 
                else:
                    if len(group_res)==0: 
                        group_res.append(dc(i))
                    else:
                        group_res[0][0].append(i[0][0]) 
                        group_res[0][1] = group_res[0][1] + i[1]
                        group_res[0][2].append(i[2][0]) 
                        for k, f in list(i[3].items()):
                            if conf_active['report_excel_fields_ids'][k][4]['group_by']:
                                continue
                            group_res[0][3][k][1] += f[1]   
            f_get_item_0 = itemgetter(0)
            f_get_item_1 = itemgetter(1)
            for rec_group_res in group_res:
                for ka, va in list(conf_active['report_excel_fields_ids'].items()):
                    if va[4]['aggregate']:
                        vals = ()
                        for n in rec_group_res[3][ka][1]:
                            val_0 = f_get_item_0(n)
                            vals += (f_get_item_1(n),)
                        try:
                            val = None
                            if va[4]['aggregate'] == 'sum':
                                n_vals = ()
                                for n in vals:
                                    if type(n) in (int, float):
                                        n_vals += (n,)
                                if len(n_vals):
                                    val = ((val_0, sum(n_vals),),)
                                else:
                                    val = ((val_0, '',),)
                            if va[4]['aggregate'] == 'avg':
                                n_vals = ()
                                for n in vals:
                                    if type(n) in (int, float):
                                        n_vals += (n,)
                                if len(n_vals):
                                    val = ((val_0, sum(n_vals)/float(len(n_vals)),),)
                                else:
                                    val = ((val_0, '',),)
                            if va[4]['aggregate'] == 'max':
                                n_vals = ()
                                for n in vals:
                                    if n not in ('',):
                                        n_vals += (n,)
                                if len(n_vals):
                                    val = ((val_0, max(n_vals),),) 
                                else:
                                    val = ((val_0, '',),)
                            if va[4]['aggregate'] == 'min':
                                n_vals = ()
                                for n in vals:
                                    if n not in ('',):
                                        n_vals += (n,)
                                if len(n_vals):
                                    val = ((val_0, min(n_vals),),) 
                                else:
                                    val = ((val_0, '',),)
                            if va[4]['aggregate'] == 'count':
                                n_vals = ()
                                for n in vals:
                                    if n not in ('',):
                                        n_vals += (n,)
                                if len(n_vals):
                                    val = ((val_0, len(n_vals),),)
                                else:
                                    val = ((val_0, '',),)
                        except TypeError as e:
                            msg = ('''ERROR WHEN CALCULATING AGGREGATE FUNCTION IN A CELL "%s" ! \n
                                    PLEASE CHECK THE PYTHON EXPRESSIONS IN FORMULA: \n%s \n
                                    ERROR: \n%s \n
                                    The aggregate function "%s" cannot be calculated for different data types!
                                    '''
                                   ) % (ka, va[4]['formulas'], e, va[4]['aggregate'])
                            raise UserError(msg)      
                        if val:                    
                            rec_group_res[3][ka][1] = val
            for r in group_res:
                data_active_res.append(r)
        having = ()
        for kf, af in  list(conf_active['report_excel_fields_ids'].items()):
            if af[4]['having_operator'] and af[4]['having_value'] is not None:
                having += ((kf,af[4]['having_operator'],af[4]['having_value'],),)
        if having_remove_ids is None:
            having_remove_ids = ()
        if len(having):
            for rec in data_active_res:
                for h in having:
                    rec_val_h = MAP_FIELD_TYPE_BLANK[conf_active['report_excel_fields_ids'][h[0]][4]['field_type']] if rec[3][h[0]][1][0][1] == '' and conf_active['report_excel_fields_ids'][h[0]][4]['field_type'] in ('integer', 'float', 'monetary', 'date', 'datetime',) else rec[3][h[0]][1][0][1] 
                    try:
                        if h[1] == "=":
                            if rec_val_h != h[2]:
                                having_remove_ids += tuple(rec[2])
                        elif h[1] == "!=":
                            if rec_val_h == h[2]:
                                having_remove_ids += tuple(rec[2])
                        elif h[1] == ">":
                            if rec_val_h <= h[2]:
                                having_remove_ids += tuple(rec[2])
                        elif h[1] == "<":
                            if rec_val_h >= h[2]:
                                having_remove_ids += tuple(rec[2])
                        elif h[1] == ">=":
                            if rec_val_h < h[2]:
                                having_remove_ids += tuple(rec[2])
                        elif h[1] == "<=":
                            if rec_val_h > h[2]:
                                having_remove_ids += tuple(rec[2])
                    except TypeError as e:
                        msg = ('''ERROR WHEN CALCULATING HAVING FUNCTION IN A CELL "%s" ! \n
                                PLEASE CHECK THE PYTHON EXPRESSIONS IN FORMULA: \n%s \n
                                ERROR: \n%s \n
                                The having function cannot be calculated for different data types!
                                '''
                               ) % (h[0], conf_active['report_excel_fields_ids'][h[0]][4]['formulas'], e,)
                        raise UserError(msg)      
            having_remove_ids = tuple(set(having_remove_ids))
            if len(having_remove_ids):
                data_tmp = []
                for rec in data_active_res:
                    if rec[2][0] not in having_remove_ids:
                        data_tmp.append(rec)
                data_active_res = dc(data_tmp)
        sort_by = []
        for k, v in list(conf_active['report_excel_fields_ids'].items()):
            if v[4]['sort_by'] and v[0][0] not in sort_by_group_key:
                sort_by.append((k, v[4]['sequence'], v[4]['sort_by'],))
        if len(sort_by):
            f_get_item_1 = itemgetter(1)
            sort_by_sorted = tuple(sorted(sort_by, key=f_get_item_1, reverse=True))  
            def get_val_sort(f, ft):
                f_get_item_1 = itemgetter(1)
                f_get_item_3 = itemgetter(3)
                f_get_item_f = itemgetter(f)
                def permutation(t,ft):
                    new_t = []
                    for n in t:
                        n0 = 0 if n[0] is None else n[0]
                        n1 = MAP_FIELD_TYPE_BLANK[ft] if n[1] == '' and ft in ('integer', 'float', 'monetary', 'date', 'datetime',) else n[1]
                        new_t.append((n1,n0,))
                    return tuple(new_t)
                return lambda *args: permutation(f_get_item_1(f_get_item_f(f_get_item_3(*args))), ft)
            for s in sort_by_sorted:
                get_val_sort_f = get_val_sort(s[0], conf_active['report_excel_fields_ids'][s[0]][4]['field_type'])
                if s[2] == 'asc':
                    reverse = False 
                else:
                    reverse = True 
                try:
                    data_active_res = sorted(data_active_res, key=get_val_sort_f, reverse=reverse)
                except TypeError as e:
                    msg = ('''ERROR DURING SORTING CELL "%s" !\n
                            PLEASE CHECK THE PYTHON EXPRESSIONS IN FORMULA : \n%s \n
                            ERROR: \n%s \n
                            Sorting can not be performed on different data types !
                            '''
                           ) % (s[0], conf_active['report_excel_fields_ids'][s[0]][4]['formulas'], e)
                    raise UserError(msg)                
        data_active['data'] = data_active_res
        if conf_active['chain_group'][-1]:
            f_get_item_1 = itemgetter(1)
            chain_ids = tuple(map(f_get_item_1, data_active['data'])) 
        else:
            chain_ids = parent_chain_ids 
        for s_id in data_active['children_ids']:
            self._post_processing_data(s_id, conf, data, chain_ids, having_remove_ids)
    def _get_start_cell(self, section_id, conf_data=None, xlsx_template=None, Rels=None):
        matrix_template = xlsx_template._conf['matrix_template']
        data_lines = conf_data['conf']['data_lines']
        col_min = data_lines['col_min']
        row_min = data_lines['row_min']
        section_cols_range = data_lines['section_boundaries'][section_id]['cols_range']
        conf_active = self._get_active_conf(section_id, conf_data['conf'])
        for k, v in list(conf_active['report_excel_fields_ids'].items()):
            related_section_ids = ()
            related_mergecell = ()
            cell_row_idx = v[0][2]-row_min
            current_section_ids = ()
            if k in xlsx_template._conf['data_line_merge_cells']:
                cols_range = xlsx_template._conf['data_line_merge_cells'][k][3]
                rows_range = xlsx_template._conf['data_line_merge_cells'][k][4]
            else:
                cols_range = (v[0][1],)
                rows_range = (v[0][2],)
            for mcol in cols_range:
                cell_row_idx_n = cell_row_idx            
                row_exist = True
                while row_exist:
                    try:
                        row = matrix_template[cell_row_idx_n]
                        section_ids = row[2][mcol-col_min][1]['section_ids']
                        mergecell = row[2][mcol-col_min][1]['mergecell_cell']
                        if cell_row_idx_n == v[0][2]-row_min:
                            if v[0][1] == mcol:
                                current_section_ids = section_ids
                            else:
                                current_section_ids = row[2][mcol-col_min][1]['section_ids'] 
                            current_mergecell = mergecell 
                            cell_row_idx_n += len(rows_range)                               
                            continue
                        if len(section_ids) > len(current_section_ids):
                            if current_section_ids == section_ids[:len(current_section_ids)]:
                                related_section_ids += (section_ids[:len(current_section_ids)+1],)
                                r_mergecell, r_sect_ids =  self._get_related_section(related_section_ids[-1], conf_data, xlsx_template, Rels)
                                related_mergecell += r_mergecell 
                                related_section_ids +=  r_sect_ids                                
                                row_exist = False
                        else:
                            if section_ids == current_section_ids:
                                if mergecell:
                                    related_mergecell += (mergecell,)                                             
                                    r_mergecell, r_sect_ids = self._get_related_mergecell(section_ids, mergecell, conf_data, xlsx_template, Rels)
                                    related_mergecell += r_mergecell 
                                    related_section_ids +=  r_sect_ids                                
                                    row_exist = False
                            else:
                                row_exist = False
                        cell_row_idx_n +=1
                    except IndexError:
                        row_exist = False
            related_section_ids = tuple(set(related_section_ids))
            related_mergecell = tuple(set(related_mergecell))
            cell_start = {}
            for col in section_cols_range:
                if col in cols_range:
                    continue
                row_exist = True
                cell_row_idx = 0
                while row_exist:
                    try:
                        row = matrix_template[cell_row_idx]
                        section_ids = row[2][col-col_min][1]['section_ids']
                        if col not in cell_start:
                            cell_start[col] = dc(row[2][col-col_min]) 
                        else:                        
                            cell_start_ids_0 = (0,) + cell_start[col][1]['section_ids'] if cell_start[col][1]['section_ids'] != (0,) else cell_start[col][1]['section_ids'] 
                            section_ids_0 = (0,) + section_ids if section_ids != (0,) else section_ids 
                            current_section_ids_0 = (0,) + current_section_ids
                            parent_level_cell_start_ids_0 = tuple(set(current_section_ids_0) & set(cell_start_ids_0))
                            parent_level_section_ids_0 = tuple(set(current_section_ids_0) & set(section_ids_0)) 
                            if parent_level_section_ids_0 < parent_level_cell_start_ids_0:
                                row_exist = False                                                
                                continue
                            else:
                                if row[2][col-col_min][1]['mergecell_cell'] in related_mergecell:
                                    cell_start[col] = dc(row[2][col-col_min]) 
                                    cell_start[col][1]['section_border'] = False                                     
                                    row_exist = False
                                    continue                                
                                related_section_bool = False
                                while len(section_ids):
                                    if section_ids in related_section_ids:
                                        related_section_bool = True
                                    section_ids = section_ids[:-1]
                                if related_section_bool:
                                    cell_start[col] = dc(row[2][col-col_min]) 
                                    cell_start[col][1]['section_border'] = False                                     
                                    row_exist = False
                                    continue                                
                                else:
                                    cell_start[col] = dc(row[2][col-col_min])                                 
                        cell_row_idx +=1
                    except IndexError:
                        row_exist = False
            conf_active['report_excel_fields_ids'][k][4]['cell_start'] = dc(cell_start)    
        for k, v in list(conf_active['children_ids'].items()):
            self._get_start_cell(k, conf_data, xlsx_template, Rels)
    def _get_start_section(self, section_id, conf_data=None, xlsx_template=None, Rels=None):
        matrix_template = xlsx_template._conf['matrix_template']
        data_lines = conf_data['conf']['data_lines']
        col_min = data_lines['col_min']
        col_max = data_lines['col_max']
        row_min = data_lines['row_min']
        cols_range = ()
        for col in range(data_lines['section_boundaries'][section_id]['min'][1], data_lines['section_boundaries'][section_id]['max'][1] + 1):
            cols_range += (col,)
        rows_range = ()
        for row in range(data_lines['section_boundaries'][section_id]['min'][2], data_lines['section_boundaries'][section_id]['max'][2] + 1):
            rows_range += (row,)
        data_lines['section_boundaries'][section_id]['cols_range'] = cols_range 
        data_lines['section_boundaries'][section_id]['rows_range'] = rows_range 
        conf_active = self._get_active_conf(section_id, conf_data['conf'])
        current_section_ids = data_lines['section_boundaries'][section_id]['section_chain_ids']    
        related_section_ids = ()
        related_mergecell = ()
        r_mergecell, r_sect_ids =  self._get_related_section(current_section_ids, conf_data, xlsx_template, Rels)
        related_mergecell += r_mergecell 
        related_section_ids +=  r_sect_ids                                
        related_mergecell = tuple(set(related_mergecell))
        related_section_ids = tuple(set(related_section_ids))
        cell_start = {}
        section_ids = ()        
        if len(current_section_ids[:-1]):
            parent_cols_range = data_lines['section_boundaries'][current_section_ids[-2]]['cols_range']
        else:
            parent_cols_range = tuple(range(col_min, col_max + 1))
        for col in parent_cols_range:
            if col in cols_range:
                continue
            row_exist = True
            cell_row_idx = 0
            while row_exist:
                try:
                    row = matrix_template[cell_row_idx]
                    section_ids = row[2][col-col_min][1]['section_ids']
                    if col not in cell_start:
                        cell_start[col] = dc(row[2][col-col_min]) 
                    else:                        
                        cell_start_ids_0 = (0,) + cell_start[col][1]['section_ids'] if cell_start[col][1]['section_ids'] != (0,) else cell_start[col][1]['section_ids'] 
                        section_ids_0 = (0,) + section_ids if section_ids != (0,) else section_ids 
                        current_section_ids_0 = (0,) + current_section_ids
                        parent_level_cell_start_ids_0 = tuple(set(current_section_ids_0) & set(cell_start_ids_0))
                        parent_level_section_ids_0 = tuple(set(current_section_ids_0) & set(section_ids_0)) 
                        if parent_level_section_ids_0 < parent_level_cell_start_ids_0:
                            row_exist = False                                                
                            continue
                        else:
                            if row[2][col-col_min][1]['mergecell_cell'] in related_mergecell:
                                cell_start[col] = dc(row[2][col-col_min]) 
                                cell_start[col][1]['section_border'] = False 
                                row_exist = False
                                continue                                
                            related_section_bool = False
                            while len(section_ids):
                                if section_ids in related_section_ids:
                                    related_section_bool = True
                                section_ids = section_ids[:-1]
                            if related_section_bool:
                                cell_start[col] = dc(row[2][col-col_min]) 
                                cell_start[col][1]['section_border'] = False 
                                row_exist = False
                                continue                                
                            else:
                                cell_start[col] = dc(row[2][col-col_min])                                 
                    cell_row_idx +=1
                except IndexError:
                    row_exist = False
        conf_active['cell_start'] = dc(cell_start)    
        for k, v in list(conf_active['children_ids'].items()):
            self._get_start_section(k, conf_data, xlsx_template, Rels)
    def _get_related_section(self, section_ids, conf_data=None, xlsx_template=None, Rels=None):
        if section_ids in Rels.sections:
            return  Rels.sections[section_ids]
        matrix_template = xlsx_template._conf['matrix_template']
        data_lines = conf_data['conf']['data_lines']
        col_min = data_lines['col_min']
        row_min = data_lines['row_min']
        conf_active = self._get_active_conf(section_ids[-1], conf_data['conf'])
        section_start = self._get_conf_coordinate(xlsx_template, conf_active['section_start'])
        section_end = self._get_conf_coordinate(xlsx_template, conf_active['section_end'])
        related_section_ids = ()
        related_mergecell = () 
        for i in range(section_start[1], section_end[1]+1):
            row_exist = True
            cell_row_idx = section_end[2]-row_min + 1 
            while row_exist:
                try:
                    row = matrix_template[cell_row_idx]
                    section_ids_tmp = row[2][i - col_min][1]['section_ids']
                    section_ids_0 = (0,) + section_ids 
                    section_ids_tmp_0 = (0,) + section_ids_tmp if section_ids_tmp != (0,) else section_ids_tmp
                    if len(section_ids_tmp_0) >= len(section_ids_0):
                        if section_ids_0[:-1] == section_ids_tmp_0[:len(section_ids_0)-1]:
                            related_section_ids += (section_ids_tmp[:len(section_ids)],)
                            r_mergecell, r_sect_ids =  self._get_related_section(section_ids_tmp[:len(section_ids)], conf_data, xlsx_template, Rels)
                            related_mergecell += r_mergecell 
                            related_section_ids +=  r_sect_ids
                            row_exist = False
                    else:
                        if section_ids_0[:-1] == section_ids_tmp_0:
                            mergecell = row[2][i-col_min][1]['mergecell_cell']                        
                            if mergecell:
                                related_mergecell += (mergecell,)                                
                                r_mergecell, r_sect_ids =  self._get_related_mergecell(section_ids[:-1], mergecell, conf_data, xlsx_template, Rels)
                                related_mergecell += r_mergecell 
                                related_section_ids +=  r_sect_ids
                                row_exist = False
                        else:
                            row_exist = False
                    cell_row_idx +=1
                except IndexError:
                    row_exist = False
        if section_ids not in Rels.sections:
            related_mergecell = tuple(set(related_mergecell))
            related_section_ids = tuple(set(related_section_ids))
            Rels(section=section_ids, rel_sections=(related_mergecell, related_section_ids,))     
        return related_mergecell, related_section_ids
    def _get_related_mergecell(self, section_ids, mergecell, conf_data=None, xlsx_template=None, Rels=None):
        if mergecell in Rels.mergecells:
            return  Rels.mergecells[mergecell]
        m_cel = mergecell
        matrix_template = xlsx_template._conf['matrix_template']
        data_lines = conf_data['conf']['data_lines']
        col_min = data_lines['col_min']
        row_min = data_lines['row_min']
        conf_active = self._get_active_conf(section_ids[-1], conf_data['conf'])
        related_mergecell = ()
        related_section_ids = ()
        cols_range = xlsx_template._conf['data_line_merge_cells'][mergecell][3]
        rows_range = xlsx_template._conf['data_line_merge_cells'][mergecell][4]
        cell_row_idx = rows_range[0]-row_min         
        for mcol in cols_range:
            cell_row_idx_n = cell_row_idx            
            row_exist = True
            while row_exist:
                try:
                    row = matrix_template[cell_row_idx_n]
                    section_ids_tmp = row[2][mcol - col_min][1]['section_ids']                        
                    mergecell = row[2][mcol-col_min][1]['mergecell_cell']
                    if cell_row_idx_n == cell_row_idx:
                        cell_row_idx_n += len(rows_range)                               
                        continue
                    if len(section_ids_tmp) > len(section_ids):
                        if section_ids == section_ids_tmp[:len(section_ids)]:
                            related_section_ids += (section_ids_tmp[:len(section_ids)+1],)
                            r_mergecell, r_sect_ids =  self._get_related_section(section_ids_tmp[:len(section_ids)+1], conf_data, xlsx_template, Rels)
                            related_mergecell += r_mergecell 
                            related_section_ids +=  r_sect_ids
                            row_exist = False
                    else:
                        if section_ids == section_ids_tmp:
                            if mergecell:
                                related_mergecell += (mergecell,)                                
                                r_mergecell, r_sect_ids =  self._get_related_mergecell(section_ids, mergecell, conf_data, xlsx_template, Rels)
                                related_mergecell += r_mergecell 
                                related_section_ids +=  r_sect_ids
                                row_exist = False
                        else:
                            row_exist = False
                    cell_row_idx_n +=1
                except IndexError:
                    row_exist = False
        if m_cel not in Rels.mergecells:
            related_mergecell = tuple(set(related_mergecell))
            related_section_ids = tuple(set(related_section_ids))
            Rels(m_cel, (related_mergecell, related_section_ids,))     
        return related_mergecell, related_section_ids
    def _preparing_data(self, section_id, conf_data=None, xlsx_template=None, res_data=None, parent_chain_ids=None):
        xlsx_conf = xlsx_template._conf
        matrix_template = xlsx_conf['matrix_template']
        data_lines = conf_data['conf']['data_lines']
        section_boundaries = data_lines['section_boundaries']
        m_cell_idx = data_lines['matrix_cell_idx']    
        section_max = data_lines['section_max']
        conf_active = self._get_active_conf(section_id, conf_data['conf'])
        data_active = self._get_active_data(section_id, conf_data['data'], conf_data['conf'])
        parent_chain_ids = ((),) if parent_chain_ids is None else parent_chain_ids
        data_row_idx_0 = True
        for data_row in data_active['data']:
            for ids in data_row[1]:
                chain_group_ind = 0
                n = 0
                for i in range(len(conf_active['chain_group'])-1):
                    if conf_active['chain_group'][n] == True:
                        chain_group_ind = n + 1
                    n += 1
                if ids[:chain_group_ind] in parent_chain_ids:
                    if not data_row_idx_0:
                        m_idx = m_cell_idx[section_boundaries[conf_active['id']]['max'][0]]
                        section_bottom_row = section_boundaries[conf_active['id']]['max'][3]
                        stack = {}
                        cell_pack = 0
                        parent_section_ids = section_boundaries[conf_active['id']]['section_chain_ids'][:-1] if len(section_boundaries[conf_active['id']]['section_chain_ids'][:-1]) else (0,) 
                        s_add_data_rows = section_boundaries[conf_active['id']]['max'][2] - section_boundaries[conf_active['id']]['min'][2] + 1
                        for s_col in section_boundaries[conf_active['id']]['cols_range']:
                            stack[s_col], cell_pack = self._get_stack(s_col, section_bottom_row + 1, res_data)
                            s_cells = []
                            for s_row in section_boundaries[conf_active['id']]['rows_range']:
                                s_cells.append(dc(matrix_template[s_row - data_lines['row_min']][2][s_col - data_lines['col_min']]))
                            self._new_coordinate(s_cells, conf_data['conf'], xlsx_template, section_bottom_row + 1)
                            s_cells.extend(stack[s_col])
                            stack[s_col] = s_cells
                        self._shift_parent_sections(section_boundaries[conf_active['id']]['section_chain_ids'], stack, s_add_data_rows, conf_data['conf'], xlsx_template, res_data)
                        self._write_stack(stack, conf_data['conf'], xlsx_template, res_data)
                    data_row_idx_0 = False
                    for item in conf_active['cell_section_order']:                        
                        if item[0]:
                            m_idx = m_cell_idx[item[1]]
                            m_cell = matrix_template[m_idx[0]][m_idx[1]][m_idx[2]]
                            if len(data_row[3][item[1]][1]) == 1:
                                res_data[m_cell[0][3]][m_cell[0][2]][1]['value'] = data_row[3][m_cell[0][0]][1][0][1]                                     
                            else:
                                c_row_range = xlsx_conf['data_line_merge_cells'][m_cell[0][0]][4] if m_cell[1]['mergecell_cell'] else (self._get_conf_coordinate(xlsx_template, m_cell[0][0])[2],) 
                                c_row_len = len(xlsx_conf['data_line_merge_cells'][m_cell[0][0]][4]) if m_cell[1]['mergecell_cell'] else 1
                                c_col_range = xlsx_conf['data_line_merge_cells'][m_cell[0][0]][3] if m_cell[1]['mergecell_cell'] else (m_cell[0][2],)
                                stack = {}
                                c_add_data_rows = (len(data_row[3][item[1]][1])-1) * len(c_row_range)
                                for c_col in c_col_range:
                                    stack[c_col], cell_pack = self._get_stack(c_col, m_cell[0][3] + c_row_len, res_data, m_cell[1]['section_ids'], c_add_data_rows)
                                    c_cells = []
                                    for value in data_row[3][m_cell[0][0]][1]:
                                        for c_row in c_row_range:
                                            c_cells.append(dc(matrix_template[c_row - data_lines['row_min']][2][c_col - data_lines['col_min']]))
                                            if c_cells[-1][0][0] == m_cell[0][0]:
                                                c_cells[-1][1]['value'] = value[1]
                                    c_cells.extend(stack[c_col])
                                    stack[c_col] = dc(c_cells)
                                for c_col, val in list(conf_active['report_excel_fields_ids'][m_cell[0][0]][4]['cell_start'].items()):
                                    m_idx = data_lines['matrix_cell_idx'][val[0][0]]    
                                    c_row = matrix_template[m_idx[0]][m_idx[1]][m_idx[2]][0][3]
                                    stack[c_col], c_pack = self._get_stack(c_col, c_row, res_data, m_cell[1]['section_ids'], c_add_data_rows)
                                    c_pack_cells = []                                        
                                    for n in range(c_add_data_rows - cell_pack + c_pack):
                                        c_pack_cells.append(val)
                                        c_pack_cells[-1][1]['pack'] = True                                            
                                        c_pack_cells[-1][1]['style'] = str(0)                                            
                                        c_pack_cells[-1][1]['section_ids'] = section_boundaries[conf_active['id']]['section_chain_ids']                                         
                                    if val[1]['section_border']:
                                        stack[c_col][1:1] = c_pack_cells
                                    else:
                                        c_pack_cells.extend(stack[c_col])
                                        stack[c_col] = dc(c_pack_cells)
                                if (c_add_data_rows - cell_pack):
                                    self._shift_parent_sections(m_cell[1]['section_ids'], stack, c_add_data_rows - cell_pack, conf_data['conf'], xlsx_template, res_data)
                                self._write_stack(stack, conf_data['conf'], xlsx_template, res_data)
                        else:
                            chain_ids = data_row[1] if conf_active['chain_group'][-1] else parent_chain_ids  
                            self._preparing_data(item[1], conf_data, xlsx_template, res_data, chain_ids)
                    break
    def _new_coordinate(self, stack, conf, xlsx_template=None, new_row_idx=None):
        xlsx_conf = xlsx_template._conf
        matrix_template = xlsx_conf['matrix_template']
        data_lines = conf['data_lines']
        section_boundaries = data_lines['section_boundaries']
        m_cell_idx = data_lines['matrix_cell_idx']         
        section_max = data_lines['section_max']
        row_idx = new_row_idx
        for n_cell in stack:
            m_idx = m_cell_idx[n_cell[0][0]]    
            m_cell = matrix_template[m_idx[0]][m_idx[1]][m_idx[2]] 
            if not n_cell[1]['pack']:
                m_cell[0][3] = row_idx                                         
            if n_cell[0][0] in section_max:
                if n_cell[1]['section_ids'] != (0,): 
                    section_ids = n_cell[1]['section_ids']
                    while len(section_ids):
                        if n_cell[0][0] == section_boundaries[section_ids[-1]]['max'][0]: 
                            section_boundaries[section_ids[-1]]['max'][3] = new_row_idx
                        section_ids = section_ids[:-1]
            row_idx += 1
    def _write_stack(self, stack, conf, xlsx_template=None, res_data=None):
        xlsx_conf = xlsx_template._conf
        matrix_template = xlsx_conf['matrix_template']
        data_lines = conf['data_lines']
        section_boundaries = data_lines['section_boundaries']
        m_cell_idx = data_lines['matrix_cell_idx']         
        section_max = data_lines['section_max']
        for n_col, col in list(stack.items()):
            m_idx = m_cell_idx[col[0][0][0]]    
            new_row_idx = matrix_template[m_idx[0]][m_idx[1]][m_idx[2]][0][3]
            for n_cell in col:
                m_idx = m_cell_idx[n_cell[0][0]]    
                m_cell = matrix_template[m_idx[0]][m_idx[1]][m_idx[2]] 
                self._ch_idx(new_row_idx, res_data)
                res_data[new_row_idx][n_col] = n_cell 
                res_data[new_row_idx][n_col][0][3] = new_row_idx
                if not n_cell[1]['pack']:
                    m_cell[0][3] = new_row_idx                                         
                if n_cell[0][0] in section_max:
                    if n_cell[1]['section_ids'] != (0,): 
                        section_ids = n_cell[1]['section_ids']
                        while len(section_ids):
                            if n_cell[0][0] == section_boundaries[section_ids[-1]]['max'][0]: 
                                section_boundaries[section_ids[-1]]['max'][3] = new_row_idx
                            section_ids = section_ids[:-1]
                new_row_idx += 1
    def _shift_parent_sections(self, section_ids, stack, row_shift, conf, xlsx_template=None, res_data=None):
        xlsx_conf = xlsx_template._conf
        matrix_template = xlsx_conf['matrix_template']
        data_lines = conf['data_lines']
        section_boundaries = data_lines['section_boundaries']
        conf_active = self._get_active_conf(section_ids[-1], conf)
        cell_pack_list_test = []
        for k_test, stack_col_test in list(stack.items()):
            stack_col_tmp_test = []
            cell_pack_tmp_test = 0
            for cell_test in stack_col_test:
                section_ids_tmp_temp = cell_test[1]['section_ids']
                section_ids_0_test = (0,) + section_ids 
                section_ids_tmp_0_test = (0,) + section_ids_tmp_temp if section_ids_tmp_temp != (0,) else section_ids_tmp_temp
                if section_ids_0_test[:-1] == section_ids_tmp_0_test and cell_pack_tmp_test < row_shift and cell_test[1]['pack']:
                    cell_pack_tmp_test += 1
            cell_pack_list_test.append(cell_pack_tmp_test)
        cell_pack =  min(cell_pack_list_test)
        for k, stack_col in list(stack.items()):
            stack_col_tmp = []
            cell_pack_tmp = 0
            for cell in stack_col:
                section_ids_tmp = cell[1]['section_ids']
                section_ids_0 = (0,) + section_ids 
                section_ids_tmp_0 = (0,) + section_ids_tmp if section_ids_tmp != (0,) else section_ids_tmp
                if section_ids_0[:-1] == section_ids_tmp_0 and cell_pack_tmp < cell_pack and cell[1]['pack']:
                    cell_pack_tmp += 1
                else:
                    stack_col_tmp.append(cell)
            if cell_pack_tmp > 0:
                stack[k] = stack_col_tmp
        parent_section_ids = section_ids[:-1] if len(section_ids) > 1 else (0,) 
        for c_col, v in list(conf_active['cell_start'].items()):
            m_idx = data_lines['matrix_cell_idx'][v[0][0]]    
            c_row = matrix_template[m_idx[0]][m_idx[1]][m_idx[2]][0][3]
            stack[c_col], c_pack = self._get_stack(c_col, c_row, res_data, parent_section_ids, row_shift)
            c_pack_cells = []                                        
            for n in range(row_shift - cell_pack + c_pack):
                c_pack_cells.append(v)
                c_pack_cells[-1][1]['pack'] = True                                            
                c_pack_cells[-1][1]['style'] = str(0)     
                c_pack_cells[-1][1]['section_ids'] = section_ids[:-1] if len(section_ids[:-1]) else (0,)
            if v[1]['section_border']:
                stack[c_col][1:1] = c_pack_cells
            else:
                c_pack_cells.extend(stack[c_col])
                stack[c_col] = dc(c_pack_cells)
        if len(section_ids[:-1]):
            self._shift_parent_sections(section_ids[:-1], stack, row_shift - cell_pack, conf, xlsx_template, res_data)
    def _get_stack(self, col, row, res_data, section_ids = None, pack = 0, reverse = False):
        stack = []
        n_pack = 0
        row_exist = True
        while row_exist:
            try:
                item = res_data[row]
                if section_ids is not None:
                    if n_pack < pack and item[col][1]['section_ids'] == section_ids  and item[col][1]['pack']: 
                        n_pack += 1
                    else:
                        stack.append(dc(item[col]))
                else:
                    stack.append(dc(item[col]))
                row +=1
            except IndexError:
                row_exist = False
        if reverse:
            stack.reverse()  
        return stack, n_pack
    def _get_order(self, section_id, conf=None, xlsx_template=None):
        conf_active = self._get_active_conf(section_id, conf)        
        sections_order = []
        f_get_item_0 = itemgetter(0)
        f_get_item_1 = itemgetter(1)
        f_get_item_2 = itemgetter(2)
        cell_section_tmp = []
        for k, v in list(conf_active['report_excel_fields_ids'].items()):
            cell_section_tmp.append((True, k, tuple(self._get_conf_coordinate(xlsx_template, k)),))
        child_sections_tmp = []
        for k, v in list(conf_active['children_ids'].items()):
            child_sections_tmp.append([(k, tuple(self._get_conf_coordinate(xlsx_template, v['section_start'])), tuple(self._get_conf_coordinate(xlsx_template, v['section_end'])),),None,None])
            cell_section_tmp.append((False, k, tuple(self._get_conf_coordinate(xlsx_template, v['section_start'])),))
        sections_order = child_sections_tmp
        conf_active['cell_section_order'] = sorted(cell_section_tmp, key=lambda x: (f_get_item_2(f_get_item_2(x)),f_get_item_1(f_get_item_2(x)),))
        for i in sections_order:
            self._get_order(i[0][0], conf, xlsx_template)
    def _ch_idx(self, i, ls):
        try:
            item = ls[i]
        except IndexError:
            ls.append([])
            ls[i] = dc(ls[0])
            for c in ls[i]:
                c[0][3] = i
    def _get_active_conf(self, section_id, conf, order=None):
        if 'data_lines' in conf and 'section_boundaries' in conf['data_lines'] and section_id in conf['data_lines']['section_boundaries']:
            section_ids = conf['data_lines']['section_boundaries'][section_id]['section_chain_ids']
            active_conf = None
            for id in section_ids:
                if active_conf is None: 
                    active_conf = conf['section'][id]
                else:
                    active_conf = active_conf['children_ids'][id]
            return active_conf
        if 'section' in conf:
            if section_id in conf['section']:
                return conf['section'][section_id]
            else:
                if len(conf['section']):
                    for k,v in list(conf['section'].items()):
                        item = self._get_active_conf(section_id, v, order) 
                        if item is not None:
                            return item                
        else:
            if section_id in conf['children_ids']:
                return conf['children_ids'][section_id]
            else:
                if len(conf['children_ids']):
                    for k,v in list(conf['children_ids'].items()):
                        item = self._get_active_conf(section_id, v, order) 
                        if item is not None:
                            return item                         
    def _get_active_data(self, section_id, data, conf, order=None):
        if 'data_lines' in conf and 'section_boundaries' in conf['data_lines'] and section_id in conf['data_lines']['section_boundaries']:
            section_ids = conf['data_lines']['section_boundaries'][section_id]['section_chain_ids']
            active_data = None
            for id in section_ids:
                if active_data is None: 
                    active_data = data[id]
                else:
                    active_data = active_data['children_ids'][id]
            return active_data        
        if 'children_ids' not in data:
            if section_id in data:
                return data[section_id]
            else:
                if len(data):
                    for k,v in list(data.items()):
                        item = self._get_active_data(section_id, v, conf, order) 
                        if item is not None:
                            return item                
        else:
            if section_id in data['children_ids']:
                return data['children_ids'][section_id]
            else:
                if len(data['children_ids']):
                    for k,v in list(data['children_ids'].items()):
                        item = self._get_active_data(section_id, v, conf, order) 
                        if item is not None:
                            return item                         
    def _get_x2many(self, model_name, comodel_name, name_field, param_id, Models_Env):
        record = self._get_model(Models_Env, model_name)[param_id]
        attrs_str = ''
        attrs_ids = None
        if len(record):
            field1 = record._fields.get(name_field)
            records_ids = field1.convert_to_read(record[field1.name], record, use_name_get=False)
            attrs = []
            for r in records_ids:
                attrs.append(self._get_model(Models_Env, comodel_name)[r])
            i = 1
            for p in attrs:
                attrs_str += p.display_name    
                if len(attrs) != i:
                    attrs_str += ', ' 
                i += 1
            attrs_ids = tuple(records_ids) 
        return ((attrs_ids, attrs_str,),)
    def _get_conf_coordinate(self, xlsx_template, coord):
        letter, row  = xlsx_template.coordinate_from_string(coord)
        letter_index = xlsx_template.column_index_from_string(letter)
        return [coord, letter_index, row]  
    def _get_model(self, Models_Env, model_name):
        if model_name in Models_Env.models:
            return Models_Env.models.get(model_name)
        else:
            model_ids = self.env[model_name].search([])
            model_ind = {}
            for r in model_ids:
                model_ind[r.id] = r
            Models_Env(model_name, model_ind)
            return Models_Env.models.get(model_name)
    def _get_field(self, Fields_Env, model_name, field_name):
        if model_name in Fields_Env.models and field_name in Fields_Env.models[model_name]:
            return Fields_Env.models.get(model_name).get(field_name)
        else:
            field = self.env[model_name].fields_get([field_name])[field_name]
            Fields_Env(model_name, field_name, field)
            return Fields_Env.models.get(model_name).get(field_name)
class ModelsEnv(object):
    def __init__(self):
        self.models = {}
    def __call__(self, model_name, model):
        self.models[model_name] = model
class FieldsEnv(object):
    def __init__(self):
        self.models = {}
    def __call__(self, model_name, field_name, field):
        if model_name in self.models:
            self.models[model_name][field_name] = field
        else:
            self.models[model_name] = {}
            self.models[model_name][field_name] = field
class Relations(object):
    def __init__(self):
        self.sections = {}
        self.mergecells = {}
    def __call__(self, mcell=None, rel_mcells=None, section=None, rel_sections=None):
        if mcell is not None:
            self.mergecells[mcell] = rel_mcells
        if section is not None:
            self.sections[section] = rel_sections
