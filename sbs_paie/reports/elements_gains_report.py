# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import Warning
from odoo.addons.sbs_utils.models.tools import format_amount_to_integer

from dateutil import relativedelta

FORMAT_DATE = "%d/%m/%Y"
FORMAT_DATE2 = "%Y-%m-%d"

MOIS = [
    'Janvier',
    'Février',
    'Mars',
    'Avril',
    'Mai',
    'Juin',
    'Juillet',
    'Aout',
    'Septembre',
    'Octobre',
    'Novembre',
    'Décembre']


class ElementsGainReport(models.AbstractModel):

    _name = 'report.aft_paie.report_elements_gains'

    @api.multi
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name(
            'aft_paie.report_elements_gains')

        # si le mois est choisi alors on ecrase la valeur de la periode
        by_month = data['form']['search_by_month']
        mois = int(data['form']['mois_de_paie'])
        filtrer = data['form']['filter_employees']

        if by_month and mois:
            oday = datetime.now()
            first_of_month = datetime.strptime(
                "1/%s/%s" % (str(mois), str(oday.year)),
                FORMAT_DATE)

            lastday = (first_of_month + relativedelta.relativedelta(
                months=+1,
                day=1,
                days=-1)).strftime(FORMAT_DATE2)

            day1 = first_of_month.strftime(FORMAT_DATE2)

            data['form']['date_to'] = lastday
            data['form']['date_from'] = day1

        # on recupere les data de la periode
        employee_ids = data['form']['employees']
        borne_max = data['form']['date_to']
        borne_min = data['form']['date_from']

        domain = []
        if borne_max and borne_min:
            domain.append(('date_to', '<=', borne_max))
            domain.append(('date_from', '>=', borne_min))

        if data['form']['lots']:
            domain.append(('payslip_run_id', 'in', data['form']['lots']))

        if filtrer and len(employee_ids) > 0:
            domain.append(('employee_id', 'in', employee_ids))

        records = self.env['hr.payslip'].search(domain)
        records = records.sorted(lambda x: x.employee_id.name)

        # calcule le nombre de jours
        debut = fields.Date.from_string(borne_min)
        fin = fields.Date.from_string(borne_max)
        nbj = (fin - debut).days

        paies = []
        totaux = {}
        to_base = 0
        to_sursal = 0
        to_transp = 0
        to_resp = 0
        to_vehicule = 0
        to_repres = 0
        to_risque = 0
        to_eau_elec = 0
        to_logement = 0
        to_sup_logement = 0
        to_brut = 0
        to_net = 0
        to_total = 0

        for record in records:
            paie = {}
            ltotal = 0
            paie['eau'] = 0
            paie['elec'] = 0
            paie['carb'] = 0
            paie['rep'] = 0
            paie['tech'] = 0
            paie['resp'] = 0
            paie['suj'] = 0

            paie['name'] = record.employee_id.name
            paie['matricule'] = "CVCV"
            paie['grille'] = record.contract_id.grille_salaire.code

            for line in record.details_by_salary_rule_category:
                if line.code == 'BASIC':
                    paie['base'] = format_amount_to_integer(line.total)
                    ltotal += line.total
                    to_base += line.total
                elif line.code == 'SURSAL':
                    paie['sursal'] = format_amount_to_integer(line.total)
                    ltotal += line.total
                    to_sursal += line.total
                elif line.code == 'TRANSPORT':
                    paie['transp'] = format_amount_to_integer(line.total)
                    ltotal += line.total
                    to_transp += line.total
                elif line.code == 'RESPONSABILITE':
                    paie['resp'] = format_amount_to_integer(line.total)
                    ltotal += line.total
                    to_transp += line.total
                elif line.code == 'VEHICULE':
                    paie['vehicule'] = format_amount_to_integer(line.total)
                    ltotal += line.total
                    to_vehicule += line.total
                elif line.code == 'REPRESENTATION':
                    paie['repres'] = format_amount_to_integer(line.total)
                    ltotal += line.total
                    to_repres += line.total
                elif line.code == 'RISQUE':
                    paie['risque'] = format_amount_to_integer(line.total)
                    ltotal += line.total
                    to_risque += line.total
                elif line.code == 'EAU_ELEC':
                    paie['eau_elec'] = format_amount_to_integer(line.total)
                    ltotal += line.total
                    to_eau_elec += line.total
                elif line.code == 'LOGEMENT':
                    paie['logem'] = format_amount_to_integer(line.total)
                    ltotal += line.total
                    to_logement += line.total
                elif line.code == 'SUP_LOGEMENT':
                    paie['sup_logem'] = format_amount_to_integer(line.total)
                    ltotal += line.total
                    to_sup_logement += line.total
                elif line.code == 'GROSS':
                    paie['brut'] = format_amount_to_integer(line.total)
                    ltotal += line.total
                    to_brut += line.total
                elif line.code == 'NET':
                    paie['net'] = format_amount_to_integer(line.total)
                    ltotal += line.total
                    to_net += line.total

            paie['ltotal'] = format_amount_to_integer(ltotal)
            to_total += ltotal
            paies.append(paie)

        totaux['base'] = format_amount_to_integer(to_base)
        totaux['sursal'] = format_amount_to_integer(to_sursal)
        totaux['transp'] = format_amount_to_integer(to_transp)
        totaux['resp'] = format_amount_to_integer(to_resp)
        totaux['vehicule'] = format_amount_to_integer(to_vehicule)
        totaux['repres'] = format_amount_to_integer(to_repres)
        totaux['risque'] = format_amount_to_integer(to_risque)
        totaux['eau_elec'] = format_amount_to_integer(to_eau_elec)
        totaux['logem'] = format_amount_to_integer(to_logement)
        totaux['sup_logem'] = format_amount_to_integer(to_sup_logement)
        totaux['brut'] = format_amount_to_integer(to_brut)
        totaux['net'] = format_amount_to_integer(to_net)
        totaux['nbj'] = nbj + 1
        totaux['debut'] = debut.strftime(FORMAT_DATE)
        totaux['fin'] = fin.strftime(FORMAT_DATE)

        if not totaux or not paies:
            raise Warning(u'Aucun bulletin de paie ne correspond\
                à votre recherche')

        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': self,
            'paies': paies,
            'totaux': totaux,
            'data': data['form']
        }

        return report_obj.render(
            'aft_paie.report_elements_gains',
            docargs)
