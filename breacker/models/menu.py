from odoo import models, fields, api

class menu(models.Model):
    _inherit = 'ir.ui.menu'

    complete_name = fields.Char(store=True)