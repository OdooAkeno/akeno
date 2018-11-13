# -*- coding: utf-8 -*-
from odoo import fields, models, _
HELP_TYPE_CONTRAT = _(u"""Cochez cette case si les ecritures comptables"""
                      u"""doivent etre générés pour ce type de contrat""")


class HrContractType(models.Model):

    _inherit = 'hr.contract.type'

    generer_facture = fields.Boolean(
        string='Ne pas générer les écritures',
        index=False,
        default=False,
        help=HELP_TYPE_CONTRAT)

    grilles_salaire = fields.Many2many(
        string='Grilles de ce type de contrat',
        readonly=False,
        required=False,
        help="grilles prises en charge par ce type de contrat",
        comodel_name='aft_paie.grille_salaire',
        relation='model_grille_to_typecontrat')

    avancement = fields.Boolean(
        string='Subit des avancements',
        default=False,
        help=""""Cochez cette case si ce type de """
             """contrat doit subir des avancements""")

    categories_bulletin = fields.Many2many(
        string='categories de bulletin',
        help="type de categorie affiche pour ce type de contrat",
        comodel_name='aft_paie.categorie_bulletin',
        relation='m2m_contracttyp_to_catbull')
