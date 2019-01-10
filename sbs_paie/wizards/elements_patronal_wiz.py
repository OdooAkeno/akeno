# -*- coding: utf-8 -*-
import time
from datetime import datetime
from dateutil import relativedelta

from odoo import api, fields, models, _

MOIS = [
    (1, 'Janvier'),
    (2, 'Février'),
    (3, 'Mars'),
    (4, 'Avril'),
    (5, 'Mai'),
    (6, 'Juin'),
    (7, 'Juillet'),
    (8, 'Aout'),
    (9, 'Septembre'),
    (10, 'Octobre'),
    (11, 'Novembre'),
    (12, 'Décembre')]

DATE_FORMAT = "%Y-%m-%d"


class ElementsPatronalPaie(models.TransientModel):
    _name = 'sbs_paie.elements_patronal_paie'

    name = fields.Char('Libelle')

    date_from = fields.Date(
        'Date From',
        default=lambda *a: time.strftime('%Y-%m-01'))

    date_to = fields.Date(
        'Date To',
        default=lambda *a: str(datetime.now() + relativedelta.relativedelta(
            months=+1,
            day=1,
            days=-1))[:10])

    search_by_month = fields.Boolean(
        'Rechercher par mois ?',
        default=True)

    mois_de_paie = fields.Selection(
        MOIS,
        default=1,
        string="Mois de la paye")

    filter_employees = fields.Boolean(
        'Choisir les employes',
        default=False)

    employees = fields.Many2many(
        'hr.employee',
        string="Liste des employes")

    lots_bulletin = fields.Many2many(
        string='Lots de bulletin de paie',
        help="Selectionnez les bulletins de paie à afficher",
        comodel_name='hr.payslip.run')

    @api.onchange('mois_de_paie', 'date_from', 'date_to')
    def onchange_mois_de_paie(self):
        self.lots_bulletin = None
        self.name = ""
        domain = []
        if self.search_by_month and self.mois_de_paie:
            oday = datetime.now()
            first_of_month = datetime.strptime(
                "%s-%s-01" % (str(oday.year), str(self.mois_de_paie)),
                DATE_FORMAT)
            lastday = (first_of_month + relativedelta.relativedelta(
                months=+1,
                day=1,
                days=-1))

            domain = [
                ('date_start', '>=', first_of_month.strftime(DATE_FORMAT)),
                ('date_end', '<=', lastday.strftime(DATE_FORMAT))]
            self.name = _("Journal des retenues patronales %s %s" % (
                first_of_month.strftime("%B"),
                first_of_month.strftime("%Y")))

        elif not self.search_by_month and self.date_from and self.date_to:
            domain = [
                ('date_start', '>=', self.date_from),
                ('date_end', '<=', self.date_to)]

        return {'domain': {'lots_bulletin': domain}}

    @api.multi
    def print_elements_patronal_paie(self):
        for record in self:
            datas = {}
            res = {}
            res['name'] = record.name
            res['date_from'] = record.date_from
            res['date_to'] = record.date_to
            res['search_by_month'] = record.search_by_month
            res['mois_de_paie'] = record.mois_de_paie
            res['filter_employees'] = record.filter_employees
            res['employees'] = [elt.id for elt in record.employees]
            res['lots'] = [elt.id for elt in record.lots_bulletin]
            datas['form'] = res

            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'sbs_paie.report_elements_patronale',
                'datas': datas,
            }
