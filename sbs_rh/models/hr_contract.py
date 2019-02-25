# -*- coding: utf-8 -*-
from odoo import fields, models


class ResBank(models.Model):

    _inherit = 'res.bank'

    # name = fields.Char(readonly=False, states={})

    # montant = fields.Float(string='Montant', required=True)
