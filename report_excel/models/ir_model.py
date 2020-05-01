# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, tools, SUPERUSER_ID, _
_logger = logging.getLogger(__name__)
class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'
    relation_model_name = fields.Char(compute='_compute_relation_model_name', string="Section Root Model", store=False)
    @api.one
    @api.model    
    def _compute_relation_model_name(self):
        if self.relation:
            self.relation_model_name = self.env['ir.model'].search([('model','=', self.relation)],[]).name
    @api.multi
    def name_get(self):
        if self._context.get('section'):
            res = []
            for field in self:
                name = '%s [%s]' % (field.field_description, field.name)
                res.append((field.id, name))
            return res
        return super(IrModelFields, self).name_get()
