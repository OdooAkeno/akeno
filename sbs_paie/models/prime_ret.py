# -*- coding: utf-8 -*-
from odoo import fields, models, _
HELP_TYPE_CONTRAT = _(u"""Cochez cette case si les ecritures comptables"""
                      u"""doivent etre générés pour ce type de contrat""")


class PrimeRet(models.Model):

    _name = 'aft_paie.prime_ret'

    regle_salariale = fields.Many2one(
        string='Regle salariale',
        required=True,
        readonly=False,
        help=u"Regle salariale lié",
        comodel_name='hr.salary.rule')

    code = fields.Char(
        string='Code',
        readonly=True,
        related="regle_salariale.code")

    name = fields.Char(
        string='Name',
        required=False,
        size=50)

    contrats = fields.Many2many(
        string='Contrats',
        readonly=True,
        help="contrats utilisant cette prime/retenue",
        comodel_name='hr.contract',
        relation='model_primeret_to_contrat')

    is_prime = fields.Boolean(
        string='Est une prime ?',
        default=True,
        help="Décochez cette case si c'est une retenue")

    montant = fields.Float(
        string='Montant',
        required=True,
        default=0.0,
        digits=(16, 2))
