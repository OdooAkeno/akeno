# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
# import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)
class ReportExcelMailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'
    @api.multi
    @api.onchange('template_id')
    def onchange_template_id_wrapper(self):
        self.ensure_one()
        values = self.onchange_template_id(self.template_id.id, self.composition_mode, self.model, self.res_id)['value']
        for fname, value in values.items():
            if not (self._context['active_model'] == 'report_excel_wizard' and fname == 'attachment_ids'):
                setattr(self, fname, value)     
