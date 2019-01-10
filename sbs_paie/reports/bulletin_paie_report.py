# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.addons.sbs_utils.models.tools import amount_to_text_fr_corrected

from dateutil import relativedelta

FORMAT_DATE = "%d/%m/%Y"
FORMAT_DATE2 = "%Y-%m-%d"


class ReportBulletinPaie(models.AbstractModel):

    _name = 'report.sbs_paie.report_bulletin_paie'

    @api.multi
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        payslip_obj = self.env['hr.payslip']
        categories_bull = self.env['sbs_paie.categorie_bulletin'].search([])

        report = report_obj._get_report_from_name(
            'sbs_paie.report_bulletin_paie')

        bulletins = payslip_obj.browse(docids)

        # recupere la liste des bulletins pour recuperer les cumuls
        cumul_bulls = payslip_obj
        for bull in bulletins:
            employee = bull.mapped('employee_id.id')
            annee_start = "%s-01-01" % bull.date_from[:4]
            annee_end = "%s-12-31" % bull.date_from[:4]
            cumul_bulls |= payslip_obj.search([
                ('employee_id', '=', employee),
                ('date_from', '>=', annee_start),
                ('date_to', '<=', annee_end)])
        datas = []

        for bull in bulletins:
            line = {}
            line['bulletin'] = bull
            line['mois'] = _(datetime.strptime(
                bull.date_from, FORMAT_DATE2).strftime('%B'))
            line['annee'] = bull.date_from[:4]

            emp_id = bull.employee_id.id
            an = line['annee']
            cumul = cumul_bulls.filtered(
                lambda x: x.employee_id.id == emp_id and x.date_from[:4] == an)
            cumul = cumul.filtered(lambda x: x.date_to <= bull.date_to)
            line['cumul'] = {}
            line['cumul']['irpp_men'] = sum(cumul.mapped('irpp_men'))
            line['cumul']['tdl'] = sum(cumul.mapped('tdl'))
            line['cumul']['cfc'] = sum(cumul.mapped('cfc'))
            line['cumul']['cnps'] = sum(cumul.mapped('cnps'))
            line['cumul']['sbt'] = sum(cumul.mapped('sbt'))

            type_con_id = bull.contract_id.type_id.id
            categories_du_bull = categories_bull.filtered(
                lambda x: type_con_id in x.types_contrat.mapped('id'))

            line['lignes'] = []
            lignes = bull.mapped('line_ids').filtered(
                lambda line: line.appears_on_payslip).filtered(
                lambda x: x.total != 0).sorted(key="sequence")
            for cat_bull in categories_du_bull:
                salary_ids = cat_bull.mapped("regles_salariales.id")
                result = lignes.filtered(
                    lambda x: x.salary_rule_id.id in salary_ids)

                if not result:
                    continue
                lignes -= result
                line['lignes'].append((cat_bull.name, result, cat_bull.nature))

            datas.append(line)

        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': self,
            'datas': datas
        }

        return report_obj.render(
            'sbs_paie.report_bulletin_paie',
            docargs)
