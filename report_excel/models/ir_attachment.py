# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, tools, SUPERUSER_ID, _
_logger = logging.getLogger(__name__)
FTYPES = ['docx', 'pptx', 'xlsx', 'opendoc', 'pdf']
class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    @api.model
    def _index(self, bin_data, datas_fname, mimetype):
        if self.res_model not in ['report.excel',]:
            for ftype in FTYPES:
                buf = getattr(self, '_index_%s' % ftype)(bin_data)
                if buf:
                    return buf
            return super(IrAttachment, self)._index(bin_data, datas_fname, mimetype)
        else:
            return
