# -*- coding: utf-8 -*-

# Copyright (C) 2018 GRIMMETTE,LLC <info@grimmette.com>

import os
import re
from sys import platform
from datetime import datetime, date
from operator import itemgetter
from io import StringIO, BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree
import tempfile
from odoo import _
from odoo.exceptions import UserError 
import logging
from copy import deepcopy as dc
_logger = logging.getLogger(__name__)
class XLSXEdit(object):
    def __init__(self, xlsx, cellutil):
        self._zip_folder = self.extract_xlsx(xlsx)
        self._data = {}
        self._res_data = None
        self._conf = {}
        self._conf['max_row_index'] = 0
        self._node_rd_attr = {}
        self._style_cat = {}
        self._style_header_data = {}
        self._zip_stream = BytesIO()
        self._row_finder = re.compile(r'\d+$')
        self._column_finder = re.compile(r'\D+$')
        self._coord_re = re.compile('^[$]?([A-Z]+)[$]?(\d+)$')
        self._coord_abs = re.compile(r'(\$?)([A-Z]{1,3})(\$?)(\d+)')
        self._RANGE_EXPR = r"""
            [$]?(?P<min_col>[A-Za-z]{1,3})?
            [$]?(?P<min_row>\d+)?
            (:[$]?(?P<max_col>[A-Za-z]{1,3})?
            [$]?(?P<max_row>\d+)?)?
            """
        self._ABSOLUTE_RE = re.compile('^' + self._RANGE_EXPR +'$', re.VERBOSE)
        self._namespaces = {
            'ws': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
            'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
            'ct': 'http://schemas.openxmlformats.org/package/2006/content-types'
        }
        self._sheet_paths = self._get_sheet_locations()
        self._sheet_ids = self._get_sheet_id()
        self._calcChain = self._check_calcChain_locations()
        self._shared_strings = None
        self._shared_strings_root = None
        self._shared_strings_index = None
        self._sheetData = {}
        self._sheetData_t = {}
        self._COL_STRING_CACHE = cellutil._COL_STRING_CACHE
        self._STRING_COL_CACHE = cellutil._STRING_COL_CACHE
    def extract_xlsx(self,xlsx):
        tmp_dir = tempfile.gettempdir()
        zip_tmp_dir = tempfile.mkdtemp(prefix='xlsx.tmp.', dir=tmp_dir)
        z = ZipFile(xlsx)
        z.extractall(zip_tmp_dir)
        z.close()
        return zip_tmp_dir
    def update_conf(self, conf_data, row_footer_data_min_index, res_data):
        self._conf['next_row_data_lines_out_index'] = len(res_data)
        self._res_data = res_data
    def check_conf(self, conf_data):
        if conf_data['sheet_reference'] in self._sheet_paths:
            return True
        else:
            return False
    def write_conf(self, conf_data):
        sheet_file = self._sheet_paths[conf_data['sheet_reference']]
        xml = self._get_xml(sheet_file)
        self._conf['sheet_reference'] = conf_data['sheet_reference']
        row_min_ind = conf_data['data_lines']['row_min']
        row_max_ind = conf_data['data_lines']['row_max']
        col_min_ind = conf_data['data_lines']['col_min']
        col_max_ind = conf_data['data_lines']['col_max']
        self._conf['row_data_min'] = row_min_ind
        self._conf['row_data_max'] = row_max_ind
        self._conf['data_line_merge_cells'] = {}
        pattern = '/ws:worksheet/ws:mergeCells'
        node_mergeCells = xml.xpath(pattern, namespaces=self._namespaces)
        if len(node_mergeCells):
            node_mergeCells_child = node_mergeCells[0].getchildren()
            if len(node_mergeCells_child):
                for node_mergeCell in node_mergeCells_child:
                    attr_ref = node_mergeCell.get('ref')
                    st, en = attr_ref.split(":")
                    col_1,row_1 = self.coordinate_from_string(st)
                    col_2,row_2 = self.coordinate_from_string(en)
                    col_1_ind= int(self.column_index_from_string(col_1))
                    col_2_ind= int(self.column_index_from_string(col_2))                    
                    if row_1 >= row_min_ind and row_1 <= self._conf['row_data_max'] and col_1_ind >= col_min_ind  and col_1_ind <= col_max_ind :
                        self._conf['data_line_merge_cells'][st] = [st,en,[col_1, row_1, col_2, row_2, col_1_ind, col_2_ind],
                                                                   tuple(range(col_1_ind, col_2_ind + 1)),
                                                                   tuple(range(row_1, row_2 + 1))
                                                                   ]
        pattern_params_r = {'row': row_min_ind }
        pattern_r = '/ws:worksheet/ws:sheetData/ws:row[@r>="%(row)s"]' % pattern_params_r
        node_rd = xml.xpath(pattern_r, namespaces=self._namespaces)
        self._conf['data_lines_style'] = {}
        self._conf['_node_rd_attr'] = {}
        if len(node_rd):
            for node_row in node_rd:
                if int(node_row.get('r')) <= self._conf['row_data_max'] :    
                    self._conf['data_lines_style'][int(node_row.get('r'))] = {} 
                    rd_childs = node_row.getchildren()
                    for rd in rd_childs:
                        cell_r = rd.get('r')
                        cell_r_letter,ind = self.coordinate_from_string(cell_r)
                        cell_s = rd.get('s')
                        merge_cells_key_present = cell_r in self._conf['data_line_merge_cells']
                        self._conf['data_lines_style'][int(node_row.get('r'))][cell_r_letter] = [
                            [cell_r, cell_r_letter, ind],
                            cell_s, 
                            merge_cells_key_present]
                    self._conf['_node_rd_attr'][int(node_row.get('r'))] = dict(node_row.attrib) 
        matrix_template = [[False, a, None] for a in range(row_min_ind, row_max_ind + 1)]
        for i in matrix_template:
            i[2] = [[[self.cell_from_index(a,i[1]),self.get_column_letter(a),a,i[1]],{'section_ids':(0,),'present':False,'style':0,'mergecell':False,'formula':False, 'pack': False, 'value':None,'mergecell_cell':False, 'section_border': True}] for a in range(col_min_ind, col_max_ind + 1)]
        sections_ids = []
        for k,v in list(conf_data['data_lines']['section_boundaries'].items()):
            sections_ids.append(v['section_chain_ids'])
        sections_ids_sorted = sorted(sections_ids)
        for s_ids in sections_ids_sorted:
            scope = conf_data['data_lines']['section_boundaries'][s_ids[-1]]
            for i in range(scope['min'][2], scope['max'][2]+1):
                rm = matrix_template[i-row_min_ind]
                for cell in rm[2]:
                    if scope['min'][1] <= cell[0][2] <= scope['max'][1]:
                        cell[1]['section_ids'] =  s_ids
        for k, v in list(self._conf['data_lines_style'].items()):
            rm = matrix_template[k-row_min_ind]
            rm[0] = True
            for ck, cv in list(v.items()):
                for cell_matrix in rm[2]: 
                    if cell_matrix[0][0] == cv[0][0]: 
                        cell_matrix[1]['present'] = True
                        cell_matrix[1]['style'] = cv[1]
                        cell_matrix[1]['mergecell'] = cv[2]
        for k, v in list(self._conf['data_line_merge_cells'].items()):
            for row in v[4]:
                rm = matrix_template[row - row_min_ind]
                for col in v[3]:
                    rm[2][col - col_min_ind][1]['mergecell_cell'] = k
        self._conf['matrix_template'] = matrix_template
        return self._conf
    def _get_row_style(self, row):
        return 1
    def write(self, sheet, cell, value, level="0", category=False, cell_ext=False):
        if value not in (True, False, None) and type(value) not in (int, float, str, date, datetime):
            if type(value) in (bytes,):
                value =  value.decode('utf-8')
            else:   
                raise TypeError('Only None, int, float, str, unicode')
        if sheet not in self._data:
            self._data[sheet] = {}
        self._data[sheet][cell] = [value, str(level), category, cell_ext]
    def get_content(self):
        exclude_files = ['/%s' % e[1] for e in list(self._sheet_paths.items()) if e[0] in list(self._data.keys())]
        exclude_files.append('/xl/sharedStrings.xml')
        exclude_files.append('/xl/workbook.xml')
        exclude_files.append('[Content_Types].xml')
        exclude_files.append('/xl/_rels/workbook.xml.rels')
        if self._calcChain:
            exclude_files.append('/xl/calcChain.xml')
        exclude_files = [re.sub(r"\\","/",x) for x in exclude_files]        
        zip_file = self._create_base_zip(exclude_files=exclude_files)
        self._add_changes(zip_file)
        if self._shared_strings:
            zip_file.writestr('xl/sharedStrings.xml', 
                              etree.tostring(self._shared_strings, 
                                             xml_declaration=True, 
                                             encoding="UTF-8", 
                                             standalone="yes"))
        else:
            try:
                zip_file.writestr('xl/sharedStrings.xml', 
                                  etree.tostring(self._get_xml('xl/sharedStrings.xml'),
                                                 xml_declaration=True, 
                                                 encoding="UTF-8", 
                                                 standalone="yes"))
            except:
                pass
        zip_file.writestr('xl/workbook.xml', 
                          etree.tostring(self._get_xml('xl/workbook.xml'),
                                         xml_declaration=True, 
                                         encoding="UTF-8", 
                                         standalone="yes"))
        zip_file.writestr('[Content_Types].xml', 
                          etree.tostring(self._get_xml('[Content_Types].xml'),
                                         xml_declaration=True, 
                                         encoding="UTF-8", 
                                         standalone="yes"))
        zip_file.writestr('xl/_rels/workbook.xml.rels', 
                          etree.tostring(self._get_xml('xl/_rels/workbook.xml.rels'),
                                         xml_declaration=True, 
                                         encoding="UTF-8", 
                                         standalone="yes"))
        if self._calcChain:
            zip_file.writestr('xl/calcChain.xml', 
                              etree.tostring(self._get_xml('xl/calcChain.xml'),
                                             xml_declaration=True, 
                                             encoding="UTF-8", 
                                             standalone="yes"))
        zip_file.close()
        return self._zip_stream.getvalue()
    def _get_xml(self, file_path):
        return etree.parse(os.path.join(self._zip_folder, file_path))
    def _init_shared_strings(self):
        try:
            self._shared_strings = self._get_xml('xl/sharedStrings.xml')
        except:
            sharedStrings_xml = etree.ElementTree(etree.fromstring(
                '''<sst count="0" uniqueCount="0" xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"></sst>'''))
            with open(os.path.join(self._zip_folder, 'xl/sharedStrings.xml'), 'wb') as sharedStrings_out:
                sharedStrings_xml.write(sharedStrings_out,
                                    xml_declaration=True, 
                                    encoding="UTF-8", 
                                    standalone="yes")
            Content_Types_xml = self._get_xml('[Content_Types].xml')
            Content_Types_root = Content_Types_xml.xpath('/ct:Types', namespaces=self._namespaces)[0]
            Content_Types_root.append(etree.Element('Override', PartName="/xl/sharedStrings.xml", ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"))
            with open(os.path.join(self._zip_folder, '[Content_Types].xml'), 'wb') as Content_Types_out:
                Content_Types_xml.write(Content_Types_out,
                                    xml_declaration=True, 
                                    encoding="UTF-8", 
                                    standalone="yes")        
            workbook_xml_rels_xml = self._get_xml('xl/_rels/workbook.xml.rels')
            workbook_xml_rels_root = workbook_xml_rels_xml.xpath('/rel:Relationships', namespaces=self._namespaces)[0]
            r_id_max = 0
            for node in workbook_xml_rels_xml.xpath('/rel:Relationships/rel:Relationship', namespaces=self._namespaces):
                r_id = node.attrib['Id']
                n_id = int(r_id[3:])
                r_id_max = n_id if n_id > r_id_max else r_id_max
            r_id_new = "rId"+ str(r_id_max + 1) 
            workbook_xml_rels_root.append(etree.Element('Relationship', Id=r_id_new, Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings", Target="sharedStrings.xml"))
            with open(os.path.join(self._zip_folder, 'xl/_rels/workbook.xml.rels'), 'wb') as workbook_xml_rels_out:
                workbook_xml_rels_xml.write(workbook_xml_rels_out,
                                    xml_declaration=True, 
                                    encoding="UTF-8", 
                                    standalone="yes")        
            self._shared_strings = self._get_xml('xl/sharedStrings.xml')
        self._shared_strings_root = self._shared_strings.xpath('/ws:sst', namespaces=self._namespaces)[0]
        try:
            self._shared_strings_index = int(self._shared_strings_root.attrib['uniqueCount'])
        except:
            self._shared_strings_root.set('count',"0")
            self._shared_strings_root.set('uniqueCount',"0")
            self._shared_strings_index = int(self._shared_strings_root.attrib['uniqueCount'])
    def _add_shared_string(self, value):
        if self._shared_strings is None:
            self._init_shared_strings()
        node_t = etree.Element('t')
        node_t.text = value
        node_si = etree.Element('si')
        node_si.append(node_t)
        self._shared_strings_root.append(node_si)
        self._shared_strings_index += 1
        return (self._shared_strings_index - 1)
    def _get_sheet_locations(self):
        sheets_id = {}
        workbook_xml = self._get_xml('xl/workbook.xml')
        for sheet_xml in workbook_xml.xpath('/ws:workbook/ws:sheets/ws:sheet', namespaces=self._namespaces):
            sheet_name = sheet_xml.attrib['name']
            sheet_rid = sheet_xml.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            sheets_id[sheet_rid] = sheet_name
        paths = {}
        xml = self._get_xml('xl/_rels/workbook.xml.rels')
        for node in xml.xpath('/rel:Relationships/rel:Relationship', namespaces=self._namespaces):
            r_id = node.attrib['Id']
            path = os.path.join('xl', node.attrib['Target'])
            if r_id in sheets_id:
                sheet_label = sheets_id[r_id]
                paths[sheet_label] = path
        return paths    
    def _get_sheet_id(self):
        sheets_id = {}
        workbook_xml = self._get_xml('xl/workbook.xml')
        for sheet_xml in workbook_xml.xpath('/ws:workbook/ws:sheets/ws:sheet', namespaces=self._namespaces):
            sheet_name = sheet_xml.attrib['name']
            sheet_id = sheet_xml.attrib['sheetId']
            sheets_id[sheet_name] = sheet_id 
        return sheets_id   
    def _check_calcChain_locations(self):
        xml = self._get_xml('xl/_rels/workbook.xml.rels')
        pattern_params = {'Target': 'calcChain.xml'}
        pattern_r = '/rel:Relationships/rel:Relationship[@Target="%(Target)s"]' % pattern_params
        node_Relationship = xml.xpath(pattern_r, namespaces=self._namespaces)
        if len(node_Relationship) :
            return True
        else:
            return False
    def _create_base_zip(self, exclude_files):
        zip_file = ZipFile(self._zip_stream, mode='w', compression=ZIP_DEFLATED, allowZip64=True)
        for path, dirs, files in os.walk(self._zip_folder):
            rel_path = path[len(self._zip_folder):]
            for file_name in files:
                if rel_path == '':
                    zip_name = file_name
                else:
                    zip_name = os.path.join(rel_path, file_name)
                zip_name = re.sub(r"\\","/", zip_name)
                if zip_name not in exclude_files:
                    zip_file.write(os.path.join(path, file_name), zip_name)
        return zip_file
    def _add_changes(self, zip_file):
        if 'sheet_reference' in self._conf:
            xml = self._get_xml(self._sheet_paths[self._conf['sheet_reference']])
            row_index = '1'
            pattern_params = {'row_index': row_index}
            pattern_r = '/ws:worksheet/ws:sheetData/ws:row[@r="%(row_index)s"]' % pattern_params
            node_r = xml.xpath(pattern_r, namespaces=self._namespaces)
            if not len(node_r) :        
                pattern_sh = '/ws:worksheet/ws:sheetData' % pattern_params
                node_sh = xml.xpath(pattern_sh, namespaces=self._namespaces)
                node_r = etree.SubElement(node_sh[0], '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row', r=row_index)
                node_sh[0].insert(0, node_r)
                with open(os.path.join(self._zip_folder, self._sheet_paths[self._conf['sheet_reference']]), 'wb') as sheet_out:
                    xml.write(sheet_out,
                                        xml_declaration=True, 
                                        encoding="UTF-8", 
                                        standalone="yes")                
        for sheet_name, data in list(self._data.items()):
            sheet_file = self._sheet_paths[sheet_name]
            sheet_content = self._get_changed_sheet(sheet_file=sheet_file, data=data)
            zip_file.writestr(sheet_file, sheet_content)
    def _get_changed_sheet(self, sheet_file, data):
        xml = self._get_xml(sheet_file)
        xmlt = self._get_xml(sheet_file)
        self._del_data_cell(xml)
        for row in xml.xpath('/ws:worksheet/ws:sheetData/ws:row', namespaces=self._namespaces):
            self._sheetData[int(row.attrib.get('r'))] = {'row':row}
            if 'cell' not in self._sheetData[int(row.attrib.get('r'))]:
                self._sheetData[int(row.attrib.get('r'))]['cell'] = {}
            for cell in row:
                self._sheetData[int(row.attrib.get('r'))]['cell'][self.column_index_from_string(self.coordinate_from_string(cell.attrib.get('r'))[0])] = cell
        for row in xmlt.xpath('/ws:worksheet/ws:sheetData/ws:row', namespaces=self._namespaces):
            self._sheetData_t[int(row.attrib.get('r'))] = {'row':row}
            if 'cell' not in self._sheetData_t[int(row.attrib.get('r'))]:
                self._sheetData_t[int(row.attrib.get('r'))]['cell'] = {}
            for cell in row:
                self._sheetData_t[int(row.attrib.get('r'))]['cell'][self.column_index_from_string(self.coordinate_from_string(cell.attrib.get('r'))[0])] = cell
        self._add_empty_cell(xml, xmlt)
        for row in self._res_data:
            for item in row:
                if item[0][0] is not None  and not item[1]['pack'] and item[1]['value'] is not None:
                    k = self.cell_from_coordinate(item[0][1], item[0][3])
                    if k in data:
                        self._change_cell(xml, k, data[k])
        if self._calcChain:
            self._fullCalcOnLoad()
        return etree.tostring(xml, xml_declaration=True, encoding="UTF-8", standalone="yes")
    def _fullCalcOnLoad(self):
        if self._calcChain:
            workbook_xml = self._get_xml('xl/workbook.xml')
            node_calcPr =  workbook_xml.xpath('/ws:workbook/ws:calcPr', namespaces=self._namespaces)
            if len(node_calcPr):
                attr = node_calcPr[0].attrib.get('fullCalcOnLoad')
                if attr is None:
                    node_calcPr[0].set('fullCalcOnLoad',"1")
                else:
                    node_calcPr[0].attrib['fullCalcOnLoad'] = "1"
            else:
                node_workbook =  workbook_xml.xpath('/ws:workbook', namespaces=self._namespaces)
                node_calcPr_attr = {'calcId':"152511", 'iterateDelta':"1E-4", 'fullCalcOnLoad':"1"}
                etree.SubElement(node_workbook[0], '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}calcPr', attrib=node_calcPr_attr)
            with open(os.path.join(self._zip_folder, 'xl/workbook.xml'), 'wb') as workbook_out:
                workbook_xml.write(workbook_out)
    def _change_cell(self, xml, cell, values):
        value = values[0]
        row_index = self._row_finder.search(cell).group()
        row_index_int = int(row_index)
        value_type = type(value)
        if value_type == bool:
            value = 'True' if value else ''
            value_type = type(value)
        node_sh = xml.xpath('/ws:worksheet/ws:sheetData', namespaces=self._namespaces)        
        cell_col_ind = self.column_index_from_string(self.coordinate_from_string(cell)[0])
        if values[3][1]['pack']:
            return 
        node_r = self._sheetData[row_index_int]['row'] if row_index_int in self._sheetData else None        
        if node_r is not None :
            node_rc = self._sheetData[row_index_int]['cell'][cell_col_ind] if cell_col_ind in self._sheetData[row_index_int]['cell'] else None
            if node_rc is not None :
                node_c = node_rc
            else:
                if len(self._sheetData[row_index_int]['cell']) :
                    node_c = etree.SubElement(node_r, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c', r=cell)
                    col_ind = cell_col_ind
                    c = True
                    while c:
                        if col_ind > 0:
                            col_ind -= 1
                            if col_ind in self._sheetData[row_index_int]['cell']:
                                ind_c = self._sheetData[row_index_int]['row'].index(self._sheetData[row_index_int]['cell'][col_ind])+1
                                self._sheetData[row_index_int]['row'].insert(ind_c, node_c)
                                self._sheetData[row_index_int]['cell'][cell_col_ind] = node_c 
                                c = False
                        else:
                            self._sheetData[row_index_int]['row'].insert(0, node_c)
                            self._sheetData[row_index_int]['cell'][cell_col_ind] = node_c 
                            c = False
                else:
                    node_c = etree.SubElement(node_r, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c', r=cell)
                    self._sheetData[row_index_int]['cell'][cell_col_ind] = node_c 
        else:
            if int(row_index) >= self._conf['row_data_min'] and int(row_index) <= self._conf['next_row_data_lines_out_index']:    
                x_row = int(self._row_finder.search(values[3][0][0]).group())
                node_rd_attr = {}
                if x_row in self._conf['_node_rd_attr']:
                    node_rd_attr = self._conf['_node_rd_attr'][x_row]
                node_rd_attr['r'] = row_index
                node_r = etree.SubElement(node_sh[0], '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row', attrib=node_rd_attr)
                r_ind = int(row_index)
                r = True
                while r:
                    if r_ind > 0:
                        r_ind -= 1
                        if r_ind in self._sheetData:
                            ind_sh = node_sh[0].index(self._sheetData[r_ind]['row'])+1
                            node_sh[0].insert(ind_sh, node_r)
                            self._sheetData[int(row_index)] = {'row': None}
                            if 'cell' not in self._sheetData[int(row_index)]:
                                self._sheetData[int(row_index)]['cell'] = {}
                            self._sheetData[int(row_index)]['row'] = node_r
                            r = False                                        
                    else:
                        node_sh[0].insert(0, node_r)
                        self._sheetData[int(row_index)] = {'row': None}
                        if 'cell' not in self._sheetData[int(row_index)]:
                            self._sheetData[int(row_index)]['cell'] = {}
                        self._sheetData[int(row_index)]['row'] = node_r
                        r = False
                node_c = etree.SubElement(node_r, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c', r=cell)
                self._sheetData[row_index_int]['cell'][cell_col_ind] = node_c                 
            else:
                node_r = etree.SubElement(node_sh[0], '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row', r=row_index)
                r_ind = int(row_index)
                r = True
                while r:
                    if r_ind > 0:
                        r_ind -= 1
                        pattern_params_rp = {'row_index': r_ind} 
                        pattern_r_prev = '/ws:worksheet/ws:sheetData/ws:row[@r="%(row_index)s"]' % pattern_params_rp
                        node_rp = xml.xpath(pattern_r_prev, namespaces=self._namespaces)
                        if len(node_rp) :
                            node_sh[0].insert(node_sh[0].index(node_rp[0])+1, node_r) 
                            r = False
                    else:
                        r = False
                node_c = etree.SubElement(node_r, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c', r=cell)
        node_v = node_c.find('ws:v', namespaces=self._namespaces)
        if node_v is None:
            node_v = etree.Element('v')
            node_c.append(node_v)
        if value == None:
            node_c.remove(node_v)
            if node_c.attrib.get('t') == 's':
                del node_c.attrib['t']
        elif value_type in (str,):
            value = str(self._add_shared_string(value))
            node_c.attrib['t'] = 's'
        else:
            if node_c.attrib.get('t') == 's':
                del node_c.attrib['t']
            if value_type == datetime:
                delta = value - datetime(1899, 12, 30)    
                value = float(delta.days) + (float(delta.seconds) / 86400)  
            if value_type == date:
                value = (value - date(1899, 12, 30)).days
        node_v.text = str(value)
        node_f = node_c.find('ws:f', namespaces=self._namespaces)
        if node_f is not None:
            node_c.remove(node_f)
            self._remove_calcChain(node_c.attrib.get('r'))
        col,row = self.coordinate_from_string(cell)
        node_row = node_c.getparent()
        x_row = int(self._row_finder.search(values[3][0][0]).group())
        if not (values[2]):
            if x_row in self._conf['data_lines_style']:
                if col in self._conf['data_lines_style'][x_row]:
                    if  self._conf['data_lines_style'][x_row][col][1]:
                        node_c.set('s', self._conf['data_lines_style'][x_row][col][1])
        pattern = '/ws:worksheet/ws:mergeCells'
        node_mergeCells = xml.xpath(pattern, namespaces=self._namespaces)
        if len(node_mergeCells):
            x_cell = ''.join([col,str(x_row)])
            if x_cell in self._conf['data_line_merge_cells']:
                conf_mergeCell = self._conf['data_line_merge_cells'][x_cell]
                dif_conf_row2 = conf_mergeCell[2][3] - conf_mergeCell[2][1]
                attr_ref_n = ''.join([conf_mergeCell[2][0],
                                      str(row),':',
                                      conf_mergeCell[2][2],
                                      str(row + dif_conf_row2)
                                      ])
                pattern_params_merg = {'attr_ref': attr_ref_n}
                pattern_mergeCell = '/ws:worksheet/ws:mergeCells/ws:mergeCell[@ref="%(attr_ref)s"]' % pattern_params_merg
                node_mergeCell_check = xml.xpath(pattern_mergeCell, namespaces=self._namespaces)
                if len(node_mergeCell_check) :
                    pass
                else:
                    etree.SubElement(node_mergeCells[0], '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}mergeCell', ref=attr_ref_n)
    def  _del_data_cell(self, xml):
        for row in self._conf['matrix_template']:
            for item in row[2]:
                pattern_params = {'row_index': str(row[1])}
                pattern_r = '/ws:worksheet/ws:sheetData/ws:row[@r="%(row_index)s"]' % pattern_params
                node_r = xml.xpath(pattern_r, namespaces=self._namespaces)
                if len(node_r) :
                    pattern_params_c = {'row_index': str(row[1]), 'cell': item[0][0]}
                    pattern_c = '/ws:worksheet/ws:sheetData/ws:row[@r="%(row_index)s"]/ws:c[@r="%(cell)s"]' % pattern_params_c
                    node_rc = xml.xpath(pattern_c, namespaces=self._namespaces)
                    if len(node_rc) :
                        if item[0][0] in self._conf['data_line_merge_cells']:
                            conf_mergeCell = self._conf['data_line_merge_cells'][item[0][0]]
                            attr_ref_n = ''.join([conf_mergeCell[2][0],
                                                  str(conf_mergeCell[2][1]),':',
                                                  conf_mergeCell[2][2],
                                                  str(conf_mergeCell[2][3])
                                                  ])
                            pattern_params_merg = {'attr_ref': attr_ref_n}
                            pattern_mergeCell = '/ws:worksheet/ws:mergeCells/ws:mergeCell[@ref="%(attr_ref)s"]' % pattern_params_merg
                            node_mergeCell_check = xml.xpath(pattern_mergeCell, namespaces=self._namespaces)
                            if len(node_mergeCell_check) :
                                node_mergeCell_check[0].getparent().remove(node_mergeCell_check[0])
                        node_f = node_rc[0].find('ws:f', namespaces=self._namespaces)
                        if node_f is not None:
                            self._remove_calcChain(node_rc[0].attrib.get('r'))                        
                        node_rc[0].getparent().remove(node_rc[0])
        if self._calcChain: 
            xml_calcChain = self._get_xml('xl/calcChain.xml')
            nodes_c = xml_calcChain.xpath('/ws:calcChain/ws:c', namespaces=self._namespaces)
            if not len(nodes_c):
                os.remove(os.path.join(self._zip_folder, 'xl/calcChain.xml'))
                xml_Content_Types = self._get_xml('[Content_Types].xml')
                for node in xml_Content_Types.xpath('/ct:Types/ct:Override', namespaces=self._namespaces):
                    if node.attrib.get('PartName') == "/xl/calcChain.xml":
                        node_Override = node
                        break
                node_Override.getparent().remove(node_Override)
                with open(os.path.join(self._zip_folder, '[Content_Types].xml'), 'wb') as Content_Types_file_out:
                    xml_Content_Types.write(Content_Types_file_out)
                xml_workbook_xml_rels = self._get_xml('xl/_rels/workbook.xml.rels')
                for node_t in xml_workbook_xml_rels.xpath('/rel:Relationships/rel:Relationship', namespaces=self._namespaces):
                    if node_t.attrib.get('Target') == "calcChain.xml":
                        node_Relationship = node_t
                        break
                node_Relationship.getparent().remove(node_Relationship)
                with open(os.path.join(self._zip_folder, 'xl/_rels/workbook.xml.rels '), 'wb') as workbook_xml_rels_file_out:
                    xml_workbook_xml_rels.write(workbook_xml_rels_file_out)
                self._calcChain = False
    def _add_empty_cell(self, xml, xmlt=None):
        node_sh = xml.xpath('/ws:worksheet/ws:sheetData', namespaces=self._namespaces)
        for row in self._res_data:
            for item in row:
                if item[0][0] is not None  and not item[1]['pack'] and item[1]['present']:
                    n_row_ind = item[0][3] 
                    if n_row_ind >= self._conf['row_data_min']:
                        t_row_ind = int(self._row_finder.search(item[0][0]).group())                        
                        node_r = self._sheetData[n_row_ind]['row'] if n_row_ind in self._sheetData else None
                        if node_r is not None:
                            cell_st = self._conf['data_lines_style'][t_row_ind].get(item[0][1])
                            cell_check = ''.join([cell_st[0][1], str(n_row_ind)])
                            cell_check_col_ind = self.column_index_from_string(cell_st[0][1])
                            node_rc = self._sheetData[n_row_ind]['cell'][cell_check_col_ind] if cell_check_col_ind in self._sheetData[n_row_ind]['cell'] else None
                            if node_rc is not None:
                                pass
                            else:
                                node_rc_t = self._sheetData_t[t_row_ind]['cell'][item[0][2]] if item[0][2] in self._sheetData_t[t_row_ind]['cell'] else None
                                if node_rc_t is None:
                                    node_c = etree.Element('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c')
                                    if  cell_st[1] is not None:
                                        node_c.set('s', cell_st[1])
                                else:
                                    node_c = dc(node_rc_t)
                                node_c.set('r', cell_check)
                                if len(self._sheetData[n_row_ind]['cell']) :
                                    c_ind = cell_check_col_ind
                                    c = True
                                    while c:
                                        if c_ind > 0:
                                            c_ind -= 1
                                            if c_ind in self._sheetData[n_row_ind]['cell']:
                                                self._sheetData[n_row_ind]['row'].insert(self._sheetData[n_row_ind]['row'].index(self._sheetData[n_row_ind]['cell'][c_ind])+1, dc(node_c))
                                                self._sheetData[n_row_ind]['cell'][cell_check_col_ind] = self._sheetData[n_row_ind]['row'][self._sheetData[n_row_ind]['row'].index(self._sheetData[n_row_ind]['cell'][c_ind])+1] 
                                                c = False
                                        else:
                                            self._sheetData[n_row_ind]['row'].insert(0, dc(node_c))
                                            self._sheetData[n_row_ind]['cell'][cell_check_col_ind] = self._sheetData[n_row_ind]['row'][0] 
                                            c = False
                                else:
                                    self._sheetData[n_row_ind]['row'].insert(0, dc(node_c))
                                    self._sheetData[n_row_ind]['cell'][cell_check_col_ind] = self._sheetData[n_row_ind]['row'][0] 
                                node_f_c = node_c.find('ws:f', namespaces=self._namespaces)
                                if node_f_c is not None:     
                                    self._add_calc_from_template(xml, cell_check, item[0][0])
                                if  cell_st[2]:
                                    pattern = '/ws:worksheet/ws:mergeCells'
                                    node_mergeCells = xml.xpath(pattern, namespaces=self._namespaces)
                                    if len(node_mergeCells):
                                        x_cell = cell_st[0][0]
                                        if x_cell in self._conf['data_line_merge_cells']:
                                            conf_mergeCell = self._conf['data_line_merge_cells'][x_cell]
                                            dif_conf_row2 = conf_mergeCell[2][3] - conf_mergeCell[2][1]
                                            attr_ref_n = ''.join([conf_mergeCell[2][0],
                                                                  str(n_row_ind),':',
                                                                  conf_mergeCell[2][2],
                                                                  str(n_row_ind + dif_conf_row2)
                                                                  ])
                                            pattern_params_merg = {'attr_ref': attr_ref_n}
                                            pattern_mergeCell = '/ws:worksheet/ws:mergeCells/ws:mergeCell[@ref="%(attr_ref)s"]' % pattern_params_merg
                                            node_mergeCell_check = xml.xpath(pattern_mergeCell, namespaces=self._namespaces)
                                            if len(node_mergeCell_check) :
                                                pass
                                            else:
                                                etree.SubElement(node_mergeCells[0], '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}mergeCell', ref=attr_ref_n)
                        else:
                            node_rd_attr = self._conf['_node_rd_attr'][t_row_ind]
                            node_rd_attr['r'] = str(n_row_ind)
                            node_rn = etree.SubElement(node_sh[0], '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row', attrib=node_rd_attr)
                            r_ind = n_row_ind
                            r = True
                            while r:
                                if r_ind > 0:
                                    r_ind -= 1
                                    if r_ind in self._sheetData:
                                        node_sh[0].insert(node_sh[0].index(self._sheetData[r_ind]['row'])+1, node_rn)
                                        self._sheetData[n_row_ind] = {'row': None}
                                        if 'cell' not in self._sheetData[n_row_ind]:
                                            self._sheetData[n_row_ind]['cell'] = {}
                                        self._sheetData[n_row_ind]['row'] = node_sh[0][node_sh[0].index(self._sheetData[r_ind]['row'])+1]
                                        r = False                                        
                                else:
                                    node_sh[0].insert(0, node_rn)
                                    self._sheetData[n_row_ind] = {'row': None}
                                    if 'cell' not in self._sheetData[n_row_ind]:
                                        self._sheetData[n_row_ind]['cell'] = {}
                                    self._sheetData[n_row_ind]['row'] = node_sh[0][0] 
                                    r = False
                            cell_st = self._conf['data_lines_style'][t_row_ind].get(item[0][1])
                            cell_check = ''.join([cell_st[0][1], str(n_row_ind)])
                            cell_check_col_ind = self.column_index_from_string(cell_st[0][1])
                            node_rnc = self._sheetData[n_row_ind]['cell'][cell_check_col_ind] if cell_check_col_ind in self._sheetData[n_row_ind]['cell'] else None
                            if node_rnc is not None:
                                pass
                            else:
                                    pattern_params_c_t = {'row_index': str(t_row_ind), 'cell': item[0][0]}
                                    pattern_c_t = '/ws:worksheet/ws:sheetData/ws:row[@r="%(row_index)s"]/ws:c[@r="%(cell)s"]' % pattern_params_c_t
                                    node_rc_t = xmlt.xpath(pattern_c_t, namespaces=self._namespaces)
                                    if not len(node_rc_t):
                                        node_c = etree.Element('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c')
                                        if  cell_st[1] is not None:
                                            node_c.set('s', cell_st[1])
                                    else:
                                        node_c = dc(node_rc_t[0])                                        
                                    node_c.set('r', cell_check)
                                    if len(self._sheetData[n_row_ind]['cell']) :
                                        c_ind = cell_check_col_ind
                                        c = True
                                        while c:
                                            if c_ind > 0:
                                                c_ind -= 1
                                                if c_ind in self._sheetData[n_row_ind]['cell']:
                                                    self._sheetData[n_row_ind]['row'].insert(self._sheetData[n_row_ind].index(self._sheetData[n_row_ind]['cell'][c_ind])+1, dc(node_c))
                                                    self._sheetData[n_row_ind]['cell'][cell_check_col_ind] = self._sheetData[n_row_ind]['row'][self._sheetData[n_row_ind].index(self._sheetData[n_row_ind]['cell'][c_ind])+1] 
                                                    c = False
                                            else:
                                                self._sheetData[n_row_ind]['row'].insert(0, dc(node_c))
                                                self._sheetData[n_row_ind]['cell'][cell_check_col_ind] = self._sheetData[n_row_ind]['row'][0] 
                                                c = False
                                    else:
                                        self._sheetData[n_row_ind]['row'].insert(0, dc(node_c))
                                        self._sheetData[n_row_ind]['cell'][cell_check_col_ind] = self._sheetData[n_row_ind]['row'][0] 
                                    node_f_c = node_c.find('ws:f', namespaces=self._namespaces)
                                    if node_f_c is not None:     
                                        self._add_calc_from_template(xml, cell_check, item[0][0])
                                    if  cell_st[2]:
                                        pattern = '/ws:worksheet/ws:mergeCells'
                                        node_mergeCells = xml.xpath(pattern, namespaces=self._namespaces)
                                        if len(node_mergeCells):
                                            x_cell = cell_st[0][0]
                                            if x_cell in self._conf['data_line_merge_cells']:
                                                conf_mergeCell = self._conf['data_line_merge_cells'][x_cell]
                                                dif_conf_row2 = conf_mergeCell[2][3] - conf_mergeCell[2][1]
                                                attr_ref_n = ''.join([conf_mergeCell[2][0],
                                                                      str(n_row_ind),':',
                                                                      conf_mergeCell[2][2],
                                                                      str(n_row_ind + dif_conf_row2)
                                                                      ])
                                                pattern_params_merg = {'attr_ref': attr_ref_n}
                                                pattern_mergeCell = '/ws:worksheet/ws:mergeCells/ws:mergeCell[@ref="%(attr_ref)s"]' % pattern_params_merg
                                                node_mergeCell_check = xml.xpath(pattern_mergeCell, namespaces=self._namespaces)
                                                if len(node_mergeCell_check) :
                                                    pass
                                                else:
                                                    etree.SubElement(node_mergeCells[0], '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}mergeCell', ref=attr_ref_n)
    def _add_conditionalFormatting_data_lines(self, xml):
        if self._conf['row_data_min'] != 1: 
            r_data = self._conf['row_data_max'] - self._conf['row_data_min'] + 1
            for i in range(self._conf['row_data_min'], self._conf['next_row_data_lines_out_index']):
                pattern_cf = '/ws:worksheet/ws:conditionalFormatting'
                node_conditionalFormatting = xml.xpath(pattern_cf, namespaces=self._namespaces)
                if len(node_conditionalFormatting):
                    x_row = self._get_row_style(i)
                    if i in [self._conf['row_data_min'], self._conf['row_data_max']]:
                            for node_cf in node_conditionalFormatting:
                                attr_sqref = node_cf.get('sqref')
                                attr_sqref_split = attr_sqref.split() 
                                attr_sqref_split_n = []
                                for attr_sqref_x in attr_sqref_split: 
                                    xn = self.all_coordinates_from_string(attr_sqref_x)
                                    if len(xn):
                                        if len(xn) == 1:
                                            col_1,row_1 = self.coordinate_from_string(attr_sqref_x)
                                            if row_1 == i:
                                                if r_data == 1:
                                                    node_cf_childs = node_cf.getchildren()
                                                    coord_exist = False
                                                    if len(node_cf_childs):
                                                        for cfRule in node_cf_childs:
                                                            node_formula = cfRule.find('ws:formula', namespaces=self._namespaces)
                                                            if node_formula is not None:
                                                                f_text = node_formula.text
                                                                f_text_coords = self.all_coordinates_from_string(f_text)
                                                                if len(f_text_coords):
                                                                    coord_exist = True
                                                    if not coord_exist:
                                                        attr_sqref_n = ''.join([col_1,
                                                                              str(row_1),':',
                                                                              col_1,
                                                                              str((self._conf['next_row_data_lines_out_index'] - 1))
                                                                              ])
                                                        attr_sqref_split_n.append(attr_sqref_n)
                                                else:
                                                    pass
                                        if len(xn) == 2:
                                            col_1i,row_1,col_2i,row_2 = self.range_boundaries(attr_sqref_x)
                                            col_1 = self.get_column_letter(col_1i)
                                            col_2 = self.get_column_letter(col_2i)
                                            if row_1 == i:
                                                if r_data == 1:
                                                    node_cf_childs = node_cf.getchildren()
                                                    coord_exist = False
                                                    if len(node_cf_childs):
                                                        for cfRule in node_cf_childs:
                                                            node_formula = cfRule.find('ws:formula', namespaces=self._namespaces)
                                                            if node_formula is not None:
                                                                f_text = node_formula.text
                                                                f_text_coords = self.all_coordinates_from_string(f_text)
                                                                if len(f_text_coords):
                                                                    coord_exist = True
                                                    addl_shift = row_2 - row_1
                                                    if not coord_exist:
                                                        attr_sqref_n = ''.join([col_1,
                                                                              str(row_1),':',
                                                                              col_2,
                                                                              str((self._conf['next_row_data_lines_out_index'] - 1 + addl_shift))
                                                                              ])
                                                        attr_sqref_split_n.append(attr_sqref_n)
                                                else:
                                                    node_cf_childs = node_cf.getchildren()
                                                    coord_exist = False
                                                    if len(node_cf_childs):
                                                        for cfRule in node_cf_childs:
                                                            node_formula = cfRule.find('ws:formula', namespaces=self._namespaces)
                                                            if node_formula is not None:
                                                                f_text = node_formula.text
                                                                f_text_coords = self.all_coordinates_from_string(f_text)
                                                                if len(f_text_coords):
                                                                    coord_exist = True
                                                    if not coord_exist:
                                                        if (row_2 - row_1 + 1) >= r_data:
                                                            addl_shift = (row_2 - row_1 + 1) - r_data
                                                            attr_sqref_n = ''.join([col_1,
                                                                                  str(row_1),':',
                                                                                  col_2,
                                                                                  str((self._conf['next_row_data_lines_out_index'] - 1) + addl_shift)
                                                                                  ])
                                                            attr_sqref_split_n.append(attr_sqref_n)
                                node_cf.set('sqref', ' '.join(attr_sqref_split_n))                                         
                    else:
                        for node_cf in node_conditionalFormatting:
                            attr_sqref = node_cf.get('sqref')
                            attr_sqref_split = attr_sqref.split() 
                            attr_sqref_split_n = []
                            node_cf_n = dc(node_cf)
                            for attr_sqref_x in attr_sqref_split: 
                                xn = self.all_coordinates_from_string(attr_sqref_x)
                                if len(xn):
                                    if len(xn) == 1:
                                        col_1,row_1 = self.coordinate_from_string(attr_sqref_x)
                                        if row_1 == x_row:
                                            node_cf_childs = node_cf.getchildren()
                                            coord_exist = False
                                            if len(node_cf_childs):
                                                for cfRule in node_cf_childs:
                                                    node_formula = cfRule.find('ws:formula', namespaces=self._namespaces)
                                                    if node_formula is not None:
                                                        f_text = node_formula.text
                                                        f_text_coords = self.all_coordinates_from_string(f_text)
                                                        if len(f_text_coords):
                                                            coord_exist = True
                                            if coord_exist:
                                                row_shift = i - x_row
                                                parent_node_cf = node_cf.getparent()
                                                attr_sqref_n = ''.join([col_1,
                                                                      str(row_1 + row_shift)
                                                                      ])
                                                attr_sqref_split_n.append(attr_sqref_n)
                                                node_cf_n_childs = node_cf_n.getchildren()
                                                if len(node_cf_n_childs):
                                                    for cfRule in node_cf_n_childs:
                                                        node_formula = cfRule.find('ws:formula', namespaces=self._namespaces)
                                                        if node_formula is not None:
                                                            f_text = node_formula.text
                                                            f_text_coords = self.all_coordinates_from_string(f_text)
                                                            if len(f_text_coords):
                                                                f_text_coords_n = []
                                                                for coord in f_text_coords:
                                                                    x_coord = self.coordinate_from_string_abs(coord)
                                                                    if not x_coord[3]:
                                                                        row_ind_n = str(int(x_coord[1]) + row_shift)
                                                                        col_abs = ''
                                                                        row_abs = ''
                                                                        if x_coord[2]:
                                                                            col_abs = '$'
                                                                        f_text_coords_n.append(''.join([col_abs, x_coord[0], row_abs, row_ind_n]))
                                                                    else:
                                                                        f_text_coords_n.append(coord)
                                                                i = 0
                                                                for n_coord in f_text_coords:
                                                                    f_text  = f_text.replace(n_coord,f_text_coords_n[i], 1)
                                                                    i += 1
                                                                node_formula.text = f_text
                                                parent_node_cf.insert(parent_node_cf.index(node_cf)+1, node_cf_n)
                                    elif len(xn) == 2:
                                        col_1i,row_1,col_2i,row_2 = self.range_boundaries(attr_sqref_x)
                                        col_1 = self.get_column_letter(col_1i)
                                        col_2 = self.get_column_letter(col_2i)
                                        if row_1 == x_row:
                                            node_cf_childs = node_cf.getchildren()
                                            coord_exist = False
                                            if len(node_cf_childs):
                                                for cfRule in node_cf_childs:
                                                    node_formula = cfRule.find('ws:formula', namespaces=self._namespaces)
                                                    if node_formula is not None:
                                                        f_text = node_formula.text
                                                        f_text_coords = self.all_coordinates_from_string(f_text)
                                                        if len(f_text_coords):
                                                            coord_exist = True
                                            if coord_exist:
                                                row_shift = i - x_row
                                                parent_node_cf = node_cf.getparent()
                                                attr_sqref_n = ''.join([col_1,
                                                                      str(row_1 + row_shift),':',
                                                                      col_2,
                                                                      str(row_2 + row_shift)
                                                                      ])
                                                attr_sqref_split_n.append(attr_sqref_n)
                                                node_cf_n_childs = node_cf_n.getchildren()
                                                if len(node_cf_n_childs):
                                                    for cfRule in node_cf_n_childs:
                                                        node_formula = cfRule.find('ws:formula', namespaces=self._namespaces)
                                                        if node_formula is not None:
                                                            f_text = node_formula.text
                                                            f_text_coords = self.all_coordinates_from_string(f_text)
                                                            if len(f_text_coords):
                                                                f_text_coords_n = []
                                                                for coord in f_text_coords:
                                                                    x_coord = self.coordinate_from_string_abs(coord)
                                                                    if not x_coord[3]:
                                                                        row_ind_n = str(int(x_coord[1]) + row_shift)
                                                                        col_abs = ''
                                                                        row_abs = ''
                                                                        if x_coord[2]:
                                                                            col_abs = '$'
                                                                        f_text_coords_n.append(''.join([col_abs, x_coord[0], row_abs, row_ind_n]))
                                                                    else:
                                                                        f_text_coords_n.append(coord)
                                                                i = 0
                                                                for n_coord in f_text_coords:
                                                                    f_text  = f_text.replace(n_coord,f_text_coords_n[i], 1)
                                                                    i += 1
                                                                node_formula.text = f_text
                                                parent_node_cf.insert(parent_node_cf.index(node_cf)+1, node_cf_n)
                            if len(attr_sqref_split_n):    
                                node_cf_n.set('sqref', ' '.join(attr_sqref_split_n))                                         
    def _remove_calcChain(self, cell):
        if self._calcChain: 
            col,row = self.coordinate_from_string(cell)
            xml_calcChain = self._get_xml('xl/calcChain.xml')
            sheetId = self._sheet_ids[self._conf['sheet_reference']]
            pattern_params_i = {'sheetId': sheetId}
            pattern_i = '/ws:calcChain/ws:c[@i="%(sheetId)s"]' % pattern_params_i
            nodes_c = xml_calcChain.xpath(pattern_i, namespaces=self._namespaces)
            if len(nodes_c):
                for node_c in nodes_c:
                    if node_c.get('r') == cell:
                        node_c.getparent().remove(node_c)
                with open(os.path.join(self._zip_folder, 'xl/calcChain.xml'), 'wb') as calcChain_file_out:
                    xml_calcChain.write(calcChain_file_out)
    def _add_calc_from_template(self, xml, cell, cell_t):
        row = int(self._row_finder.search(cell).group())
        x_row = int(self._row_finder.search(cell_t).group())               
        row_shift = int(row) - int(x_row)
        pattern_params_c_n = {'row_index': str(row), 'cell': cell}
        pattern_c_n = '/ws:worksheet/ws:sheetData/ws:row[@r="%(row_index)s"]/ws:c[@r="%(cell)s"]' % pattern_params_c_n
        node_rc_n = xml.xpath(pattern_c_n, namespaces=self._namespaces)
        if len(node_rc_n):
            node_f_n = node_rc_n[0].find('ws:f', namespaces=self._namespaces)
            if node_f_n is not None:
                f_text = node_f_n.text
                f_text_coords = self.all_coordinates_from_string(f_text)
                if len(f_text_coords):
                    f_text_coords_n = []
                    for coord in f_text_coords:
                        x_coord = self.coordinate_from_string_abs(coord)
                        if not x_coord[3]:
                            row_ind_n = str(int(x_coord[1]) + row_shift)
                            col_abs = ''
                            row_abs = ''
                            if x_coord[2]:
                                col_abs = '$'
                            f_text_coords_n.append(''.join([col_abs, x_coord[0], row_abs, row_ind_n]))
                        else:
                            f_text_coords_n.append(coord)
                    i = 0
                    for n_coord in f_text_coords:
                        f_text  = f_text.replace(n_coord,f_text_coords_n[i], 1)
                        i += 1
                    node_f_n.text = f_text
                    if self._calcChain: 
                        xml_calcChain = self._get_xml('xl/calcChain.xml')
                        nodes_c = xml_calcChain.xpath('/ws:calcChain', namespaces=self._namespaces)
                        node_c = etree.SubElement(nodes_c[0], '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c', r=cell, i=self._sheet_ids[self._conf['sheet_reference']])
                        nodes_c[0].append(node_c)     
                        with open(os.path.join(self._zip_folder, 'xl/calcChain.xml'), 'wb') as calcChain_file_out:
                            xml_calcChain.write(calcChain_file_out)
    def add_autofilter(self, xml_sheet):
        pattern_sh = '/ws:worksheet/ws:sheetData'
        node_sh = xml_sheet.xpath(pattern_sh, namespaces=self._namespaces)[0]
        range_autoFilter = ''.join([self._conf['col_header'],
                                    str(self._conf['row_header']),':',
                                    self._conf['max_column'],
                                    str(self._conf['max_row_index'])
                                    ])
        parent_wsh = node_sh.getparent()
        node_autoFilter = etree.SubElement(parent_wsh, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}autoFilter', ref=range_autoFilter)
        parent_wsh.insert(parent_wsh.index(node_sh)+1, node_autoFilter)        
        xml_workbook = self._get_xml('xl/workbook.xml')
        definedName_text = ''.join([self._conf['sheet_reference'],'!',
                                    '$',self._conf['col_header'],
                                    '$',str(self._conf['row_header']),':',
                                    '$',self._conf['max_column'],
                                    '$',str(self._conf['max_row_index'])
                                    ])
        pattern_params_sheet = {'sheet_name': self._conf['sheet_reference']}
        pattern_sheet = '/ws:workbook/ws:sheets/ws:sheet[@name="%(sheet_name)s"]' % pattern_params_sheet
        node_sheet = xml_workbook.xpath(pattern_sheet, namespaces=self._namespaces)[0]
        localSheetId = node_sheet.getparent().index(node_sheet) 
        attr_dn = {'function':"false", 'name':"_xlnm._FilterDatabase", 'localSheetId':str(localSheetId), 'hidden':"1", 'vbProcedure':"false"}
        pattern_dns = '/ws:workbook/ws:definedNames'
        node_definedNames = xml_workbook.xpath(pattern_dns, namespaces=self._namespaces)
        if len(node_definedNames):
            node_definedName = etree.SubElement(node_definedNames[0], '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}definedName', attrib=attr_dn)
            node_definedNames[0].insert(0, node_definedName)        
            node_definedName.text = definedName_text
        else:
            pattern_wbsh = '/ws:workbook/ws:sheets'
            node_sheets = xml_workbook.xpath(pattern_wbsh, namespaces=self._namespaces)[0]
            parent_wbsh = node_sheets.getparent()
            node_definedNames = etree.SubElement(parent_wbsh, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}definedNames')
            parent_wbsh.insert(parent_wbsh.index(node_sheets)+1, node_definedNames)        
            node_definedName = etree.SubElement(node_definedNames, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}definedName', attrib=attr_dn)
            node_definedNames.insert(0, node_definedName)        
            node_definedName.text = definedName_text
        with open(os.path.join(self._zip_folder, 'xl/workbook.xml'), 'wb') as workbook_file_out:
            xml_workbook.write(workbook_file_out)
    def shift_coordinate_row(self, sheet_name, row_start='1', row_shift='0'):
        sheet_file = self._sheet_paths[sheet_name]
        xml = self._get_xml(sheet_file)
        if row_shift:
            pattern_params_r = {'row': row_start}
            pattern_r = '/ws:worksheet/ws:sheetData/ws:row[@r>="%(row)s"]' % pattern_params_r
            node_rd = xml.xpath(pattern_r, namespaces=self._namespaces)
            if len(node_rd):
                for node_row in node_rd:
                    r = node_row.get('r')
                    node_row.set('r', str(int(node_row.get('r')) + row_shift))
                    rd_childs = node_row.getchildren()
                    for rd in rd_childs:
                        cell_r = rd.get('r')
                        col,row = self.coordinate_from_string(cell_r)
                        new_coord = ''.join([col, str(row + row_shift)])
                        rd.set('r', new_coord)
                        node_f = rd.find('ws:f', namespaces=self._namespaces)
                        if node_f is not None:
                            f_text = node_f.text
                            f_text_coords = self.all_coordinates_from_string(f_text)
                            if len(f_text_coords):
                                f_text_coords_n = []
                                for coord in f_text_coords:
                                    x_coord = self.coordinate_from_string_abs(coord)
                                    if not x_coord[3]:
                                        row_ind_n = str(int(x_coord[1]) + row_shift)
                                        col_abs = ''
                                        row_abs = ''
                                        if x_coord[2]:
                                            col_abs = '$'
                                        f_text_coords_n.append(''.join([col_abs, x_coord[0], row_abs, row_ind_n]))
                                    else:
                                        f_text_coords_n.append(coord)
                                i = 0
                                for n_coord in f_text_coords:
                                    f_text  = f_text.replace(n_coord,f_text_coords_n[i], 1)
                                    i += 1
                                node_f.text = f_text
                if self._calcChain:
                    xml_calcChain = self._get_xml('xl/calcChain.xml')
                    sheetId = self._sheet_ids[sheet_name]
                    pattern_params_i = {'sheetId': sheetId}
                    pattern_i = '/ws:calcChain/ws:c[@i="%(sheetId)s"]' % pattern_params_i
                    nodes_c = xml_calcChain.xpath(pattern_i, namespaces=self._namespaces)
                    if len(nodes_c):
                        for node_c in nodes_c:
                            r = node_c.get('r')
                            col_r,row_r = self.coordinate_from_string(r)
                            if row_r >= row_start:
                                new_coord_r = ''.join([col_r, str(row_r + row_shift)])
                                node_c.set('r', new_coord_r)
                        with open(os.path.join(self._zip_folder, 'xl/calcChain.xml'), 'wb') as calcChain_file_out:
                            xml_calcChain.write(calcChain_file_out)
            pattern = '/ws:worksheet/ws:mergeCells'
            node_mergeCells = xml.xpath(pattern, namespaces=self._namespaces)
            if len(node_mergeCells):
                node_mergeCells_child = node_mergeCells[0].getchildren()
                if len(node_mergeCells_child):
                    for node_mergeCell in node_mergeCells_child:
                        attr_ref = node_mergeCell.get('ref')
                        st, en = attr_ref.split(":")
                        col_1,row_1 = self.coordinate_from_string(st)
                        col_2,row_2 = self.coordinate_from_string(en)
                        if row_1 >= row_start:
                            attr_ref_n = ''.join([col_1,
                                                  str(row_1 + row_shift),':',
                                                  col_2,
                                                  str(row_2 + row_shift)
                                                  ])
                            node_mergeCell.set('ref', attr_ref_n)
            pattern_cf = '/ws:worksheet/ws:conditionalFormatting'
            node_conditionalFormatting = xml.xpath(pattern_cf, namespaces=self._namespaces)
            if len(node_conditionalFormatting):
                for node_cf in node_conditionalFormatting:
                    attr_sqref = node_cf.get('sqref')
                    xn = self.all_coordinates_from_string(attr_sqref)
                    if len(xn):
                        if len(xn) == 1:
                            col_1,row_1 = self.coordinate_from_string(attr_sqref)
                            if row_1 >= row_start:
                                attr_sqref_n = ''.join([col_1, str(row_1 + row_shift)])
                                node_cf.set('sqref', attr_sqref_n)
                        elif len(xn) == 2:
                            col_1i,row_1,col_2i,row_2 = self.range_boundaries(attr_sqref)
                            col_1 = self.get_column_letter(col_1i)
                            col_2 = self.get_column_letter(col_2i)
                            if row_1 >= row_start:
                                attr_sqref_n = ''.join([col_1,
                                                      str(row_1 + row_shift),':',
                                                      col_2,
                                                      str(row_2 + row_shift)
                                                      ])
                                node_cf.set('sqref', attr_sqref_n)
                        if row_1 >= row_start:
                            node_cf_childs = node_cf.getchildren()
                            if len(node_cf_childs):
                                for cfRule in node_cf_childs:
                                    node_formula = cfRule.find('ws:formula', namespaces=self._namespaces)
                                    if node_formula is not None:
                                        f_text = node_formula.text
                                        f_text_coords = self.all_coordinates_from_string(f_text)
                                        if len(f_text_coords):
                                            f_text_coords_n = []
                                            for coord in f_text_coords:
                                                x_coord = self.coordinate_from_string_abs(coord)
                                                if not x_coord[3]:
                                                    row_ind_n = str(int(x_coord[1]) + row_shift)
                                                    col_abs = ''
                                                    row_abs = ''
                                                    if x_coord[2]:
                                                        col_abs = '$'
                                                    f_text_coords_n.append(''.join([col_abs, x_coord[0], row_abs, row_ind_n]))
                                                else:
                                                    f_text_coords_n.append(coord)
                                            i = 0
                                            for n_coord in f_text_coords:
                                                f_text  = f_text.replace(n_coord,f_text_coords_n[i], 1)
                                                i += 1
                                            node_formula.text = f_text
            self._print_area_shift(row_shift)
        self._print_area_check()
        with open(os.path.join(self._zip_folder, sheet_file), 'wb') as sheet_file_out:
            xml.write(sheet_file_out)
    def _print_area_check(self):
        sheet_name = self._conf['sheet_reference']
        workbook_xml = self._get_xml('xl/workbook.xml')
        count_check = 0
        if len(workbook_xml.xpath('/ws:workbook/ws:definedNames', namespaces=self._namespaces)):
            node_definedNames = workbook_xml.xpath('/ws:workbook/ws:definedNames', namespaces=self._namespaces)
            _xlnm_Print_Area = {}
            for node_definedName in node_definedNames[0]:
                f_name = node_definedName.attrib.get('name')
                f_localSheetId = node_definedName.attrib.get('localSheetId')
                if f_name.find("_xlnm.Print_Area") >= 0 : 
                    if f_name == "_xlnm.Print_Area":
                        if not f_localSheetId in _xlnm_Print_Area:
                            _xlnm_Print_Area[f_localSheetId] = "_xlnm.Print_Area"
                        else:
                            node_definedNames[0].remove(node_definedName)
                            count_check += 1
                    else:
                        node_definedNames[0].remove(node_definedName)
                        count_check += 1
            if count_check:
                with open(os.path.join(self._zip_folder, 'xl/workbook.xml'), 'wb') as workbook_out:
                    workbook_xml.write(workbook_out)
    def _print_area_shift(self, row_shift):
        sheet_name = self._conf['sheet_reference']
        workbook_xml = self._get_xml('xl/workbook.xml')
        if len(workbook_xml.xpath('/ws:workbook/ws:definedNames', namespaces=self._namespaces)):
            pattern_params_i = {'name': "_xlnm.Print_Area"}
            pattern_i = '/ws:workbook/ws:definedNames/ws:definedName[@name="%(name)s"]' % pattern_params_i
            node_definedNames = workbook_xml.xpath(pattern_i, namespaces=self._namespaces)
            if len(node_definedNames):
                for definedName in node_definedNames:
                    f_text = definedName.text
                    if f_text.find(sheet_name) >= 0 : 
                        coordinates = self.all_coordinates_from_string(f_text)
                        if len(coordinates):
                            x_coord = self.coordinate_from_string_abs(coordinates[-1])
                            row_ind_n = str(int(x_coord[1]) + row_shift)
                            col_abs = ''
                            row_abs = ''
                            if x_coord[2]:
                                col_abs = '$'
                            if x_coord[3]:
                                row_abs = '$'
                            f_text_coords_n = ''.join([col_abs, x_coord[0], row_abs, row_ind_n])
                            f_text  = f_text.replace(coordinates[-1], f_text_coords_n, 1)
                            definedName.text = f_text
                            with open(os.path.join(self._zip_folder, 'xl/workbook.xml'), 'wb') as workbook_out:
                                workbook_xml.write(workbook_out)
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
    def cell_from_coordinate(self, col_letter, row_ind):
        return ''.join([col_letter,str(row_ind)])
    def column_compare(self, cell_1, cell_2):
        col_1_letter, row_1_ind = self.coordinate_from_string(cell_1)
        col_1_ind = self.column_index_from_string(col_1_letter)
        col_2_letter, row_2_ind = self.coordinate_from_string(cell_2)
        col_2_ind = self.column_index_from_string(col_2_letter)
        if col_1_ind == col_2_ind:
            return True
        else:
            return False
    def coordinate_from_string_abs(self, coord_string):
        match = self._coord_abs.match(coord_string.upper())
        if not match:
            msg = 'Invalid range coordinates (%s)' % coord_string
            raise ValueError(msg)
        c_abs, column, r_abs, row  = match.groups()
        col_abs = False
        row_abs = False
        if c_abs == '$':
            col_abs = True
        if r_abs == '$':
            row_abs = True
        row = int(row)
        if not row:
            msg = "There is no row 0 (%s)" % coord_string
            raise ValueError(msg)
        return (column, row, col_abs, row_abs)
    def range_boundaries(self, range_string):
        m = self._ABSOLUTE_RE.match(range_string)
        if not m:
            raise ValueError("{0} is not a valid coordinate or range")
        min_col, min_row, sep, max_col, max_row = m.groups()
        if min_col is not None:
            min_col = self.column_index_from_string(min_col)
        if min_row is not None:
            min_row = int(min_row)
        if max_col is not None:
            max_col = self.column_index_from_string(max_col)
        else:
            max_col = min_col
        if max_row is not None:
            max_row = int(max_row)
        else:
            max_row = min_row
        return min_col, min_row, max_col, max_row
    def all_coordinates_from_string(self, attr_string):
        r = []       
        if  attr_string:
            for m in self._coord_abs.finditer(attr_string):
                r.append(m.group(0))
        return r
