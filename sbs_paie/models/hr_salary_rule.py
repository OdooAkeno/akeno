# -*- coding: utf-8 -*-
from odoo import fields, models


class HrSalaryRule(models.Model):

    _inherit = "hr.salary.rule"

    categories_bulletin = fields.Many2many(
        string='Categories de bulletin',
        required=False,
        help="categorie de bulletin contenant cette regle",
        comodel_name='aft_paie.categorie_bulletin',
        relation='m2m_salaryrul_to_catbull')
