# -*- coding: utf-8 -*-
from odoo import fields, models, _
HELP_TYPE_CONTRAT = _(u"""Cochez cette case si les ecritures comptables"""
                      u"""doivent etre générés pour ce type de contrat""")


class PayslipPrimes(models.Model):

    _name = 'aft_paie.payslip_primes'

    payslip = fields.Many2one(
        string='Payslip',
        required=True,
        comodel_name='hr.payslip',
        ondelete="cascade")

    state = fields.Selection(
        string='State',
        related="payslip.state",
        readonly=True)

    prime_ret = fields.Many2one(
        string='Prime/retenue',
        required=True,
        comodel_name='aft_paie.prime_ret')

    montant = fields.Float(
        string='Montant',
        related="prime_ret.montant",
        readonly=True)

    is_prime = fields.Boolean(
        related="prime_ret.is_prime",
        readonly=True)

    utiliser = fields.Boolean(
        string='Utiliser',
        readonly=False,
        default=True,
        help="Cochez cette case pour impacter le bulletin de paie")
