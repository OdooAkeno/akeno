# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

DTE_FMT = "%Y-%m-%d"
HELP_AVAN = _("Liste des avancements du personnel")


class HrContract(models.Model):

    _inherit = 'hr.contract'

    grille_salaire = fields.Many2one(
        string='Grille salariale',
        readonly=False,
        required=True,
        help="grille salariale de ce contrat",
        comodel_name='aft_paie.grille_salaire',
        track_visibility='onchange')

    wage = fields.Float(
        readonly=True,
        related="grille_salaire.montant",
        digits=(16, 2))

    primes_ret = fields.Many2many(
        string='Primes et retenues',
        help="Primes de ce contrat",
        comodel_name='aft_paie.prime_ret',
        relation='model_primeret_to_contrat',
        track_visibility='onchange')

    avancements = fields.One2many(
        string='Avancements',
        readonly=True,
        help=HELP_AVAN,
        comodel_name='aft_paie.avancement',
        inverse_name='contract_id',
        domain=[('state', '=', 'done')])

    dernier_avancement = fields.Date(
        string='Dernier avancement',
        readonly=True,
        default=fields.Date.today(),
        compute="_compute_dernier_avancement",
        help="la date de votre dernier avancement")

    @api.onchange('type_id')
    def onchange_type_id(self):
        domain = []
        if self.type_id:
            grilles_ids = self.type_id.grilles_salaire.mapped('id')
            domain = [('id', 'in', grilles_ids)]
        return {'domain': {'grille_salaire': domain}}

    @api.model
    def avancement(self):
        u"""Créé automatique les avancements du personnel."""
        anv_obj = self.env['aft_paie.avancement']
        nbr_an = self.env.user.company_id.nbr_annee_avanc
        date_fil = (datetime.now() - relativedelta(years=nbr_an)).strftime(
            "%Y-%m-%d")
        avancement_en_cours = anv_obj.search([
            ('state', 'in', ['draft', 'confirm'])])
        filtre_contrat = avancement_en_cours.mapped('contract_id.id')

        contrats = self.search([
            ('state', '=', 'open'),
            ('type_id.avancement', '=', True),
            ('id', 'not in', filtre_contrat)]).filtered(
            lambda x: x.dernier_avancement and x.dernier_avancement < date_fil)

        for cont in contrats:
            _logger.info("avancement de %s" % cont.employee_id.name)
            values = {'employee_id': cont.employee_id.id}
            anv_obj.create(values)

    @api.multi
    def _compute_dernier_avancement(self):
        for r in self:
            date = None
            if r.avancements:
                date = r.avancements[0].date_avancement
            if not date and r.date_start:
                date = r.date_start
            r.dernier_avancement = date
