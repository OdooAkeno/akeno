# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CategorieBulletin(models.Model):

    _name = "aft_paie.categorie_bulletin"
    _order = "ordre"

    name = fields.Char(
        string='Nom de la categorie',
        required=True)

    ordre = fields.Integer(
        string='Ordre',
        required=True,
        index=False,
        default=10,
        help="Ordre d'affichage des categories")

    nature = fields.Selection(
        string='Nature',
        required=True,
        default='g',
        help=False,
        selection=[('g', 'Gain'), ('r', 'Retenue')])

    regles_salariales = fields.Many2many(
        string='Regles salariales',
        required=True,
        help="Regles salariales a afficher",
        comodel_name='hr.salary.rule',
        relation='m2m_salaryrul_to_catbull')

    types_contrat = fields.Many2many(
        string='Types de contrat',
        required=True,
        help="Types de contrat utilisant cette categorie",
        comodel_name='hr.contract.type',
        relation='m2m_contracttyp_to_catbull')