# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrPayslip(models.Model):

    _inherit = 'hr.payslip'

    primes = fields.One2many(
        string='Primes et retenues',
        help=u"Liste des primes de l'employé",
        comodel_name='sbs_paie.payslip_primes',
        inverse_name='payslip',
        readonly=True,
        states={'draft': [('readonly', False)]})

    salaire_base = fields.Float(
        string='Salaire de base',
        readonly=True,
        compute="_compute_regles",
        store=True)

    sursalaire = fields.Float(
        string='Sursalaire',
        readonly=True,
        compute="_compute_regles",
        store=True)

    transport = fields.Float(
        string='Transport',
        readonly=True,
        compute="_compute_regles",
        store=True)

    responsabilite = fields.Float(
        string=u'Responsabilité',
        readonly=True,
        compute="_compute_regles",
        store=True)

    vehicule = fields.Float(
        string=u'Véhicule',
        readonly=True,
        compute="_compute_regles",
        store=True)

    representation = fields.Float(
        string=u'Représentation',
        readonly=True,
        compute="_compute_regles",
        store=True)

    risque = fields.Float(
        string=u'Risque',
        readonly=True,
        compute="_compute_regles",
        store=True)

    eau_elec = fields.Float(
        string=u'Eau electricité',
        readonly=True,
        compute="_compute_regles",
        store=True)

    logement = fields.Float(
        string=u'Logement',
        readonly=True,
        compute="_compute_regles",
        store=True)

    sup_logement = fields.Float(
        string=u'Sup Logement',
        readonly=True,
        compute="_compute_regles",
        store=True)

    salaire_brut = fields.Float(
        string=u'Salaire brut',
        readonly=True,
        compute="_compute_regles",
        store=True)

    sit = fields.Float(
        string=u'Salaire Imposable',
        readonly=True,
        compute="_compute_regles",
        store=True)

    log_paye = fields.Float(
        string=u'Logement payé',
        readonly=True,
        compute="_compute_regles",
        store=True)

    log_retenu = fields.Float(
        string=u'Logement retenu',
        readonly=True,
        compute="_compute_regles",
        store=True)

    voiture = fields.Float(
        string=u'Voiture',
        readonly=True,
        compute="_compute_regles",
        store=True)

    eau_elec_ret = fields.Float(
        string=u'Eau/electricité retenu',
        readonly=True,
        compute="_compute_regles",
        store=True)

    sbt = fields.Float(
        string=u'Salaire brut taxable',
        readonly=True,
        compute="_compute_regles",
        store=True)

    sc = fields.Float(
        string=u'Salaire cotisable',
        readonly=True,
        compute="_compute_regles",
        store=True)

    fp = fields.Float(
        string=u'FP',
        readonly=True,
        compute="_compute_regles",
        store=True)

    pvid = fields.Float(
        string=u'PVID',
        readonly=True,
        compute="_compute_regles",
        store=True)

    sni = fields.Float(
        string=u'SNI',
        readonly=True,
        compute="_compute_regles",
        store=True)

    sni_an = fields.Float(
        string=u'SNI AN',
        readonly=True,
        compute="_compute_regles",
        store=True)

    base_irpp = fields.Float(
        string=u'BaseIRPP',
        readonly=True,
        compute="_compute_regles",
        store=True)

    c1 = fields.Float(
        string=u'C1',
        readonly=True,
        compute="_compute_regles",
        store=True)

    c2 = fields.Float(
        string=u'c2',
        readonly=True,
        compute="_compute_regles",
        store=True)

    c3 = fields.Float(
        string=u'c3',
        readonly=True,
        compute="_compute_regles",
        store=True)

    c4 = fields.Float(
        string=u'c4',
        readonly=True,
        compute="_compute_regles",
        store=True)

    irpp_an = fields.Float(
        string=u'IRPP ANNUEL',
        readonly=True,
        compute="_compute_regles",
        store=True)

    irpp_men = fields.Float(
        string=u'IRPP MENSUEL',
        readonly=True,
        compute="_compute_regles",
        store=True)

    cac = fields.Float(
        string=u'CAC',
        readonly=True,
        compute="_compute_regles",
        store=True)

    cfc = fields.Float(
        string=u'CFC',
        readonly=True,
        compute="_compute_regles",
        store=True)

    rav = fields.Float(
        string=u'RAV',
        readonly=True,
        compute="_compute_regles",
        store=True)

    tdl = fields.Float(
        string=u'TDL',
        readonly=True,
        compute="_compute_regles",
        store=True)

    cnps = fields.Float(
        string=u'CNPS',
        readonly=True,
        compute="_compute_regles",
        store=True)

    retenues = fields.Float(
        string='Retenues',
        readonly=True,
        compute="_compute_regles",
        store=True)

    salaire_net = fields.Float(
        string='Salaire net',
        readonly=True,
        compute="_compute_regles",
        store=True)

    pvid_pat = fields.Float(
        string='PVID PATRO',
        readonly=True,
        compute="_compute_regles",
        store=True)

    cnps_pat = fields.Float(
        string='CNPS PATRO',
        readonly=True,
        compute="_compute_regles",
        store=True)

    acctrav_pat = fields.Float(
        string='ACCIDENT DE TRAVAIL',
        readonly=True,
        compute="_compute_regles",
        store=True)

    cfc_pat = fields.Float(
        string='CFC PATRO',
        readonly=True,
        compute="_compute_regles",
        store=True)

    fne_pat = fields.Float(
        string='FNE PATRO',
        readonly=True,
        compute="_compute_regles",
        store=True)

    retenues_pat = fields.Float(
        string='Retenues PATRO',
        readonly=True,
        compute="_compute_regles",
        store=True)

    at = fields.Float(
        string='AT',
        readonly=True,
        compute="_compute_regles",
        store=True)

    af = fields.Float(
        string='AF',
        readonly=True,
        compute="_compute_regles",
        store=True)

    primes_grat = fields.Float(
        string='Primes et gratifications',
        readonly=True,
        compute="_compute_primes_grat")

    total_hours = fields.Integer(
        compute="compute_timesheet_data")

    timesheet_hours = fields.Integer(
        compute="compute_timesheet_data")

    @api.constrains('contract_id')
    def _check_primes(self):
        pay_primes_obj = self.env['sbs_paie.payslip_primes']
        for r in self:
            r.primes.unlink()
            if r.contract_id:
                for prime_ret in r.contract_id.primes_ret:
                    line = {}
                    line['payslip'] = r.id
                    line['prime_ret'] = prime_ret.id
                    pay_primes_obj.create(line)

    @api.depends('line_ids')
    def _compute_regles(self):
        for r in self:
            r.salaire_base = 0.0
            r.sursalaire = 0.0
            r.transport = 0.0

            lns = r.line_ids

            if lns:
                line_net = lns.filtered(lambda x: x.code == "BASIC")
                r.salaire_base = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "SURSAL")
                r.sursalaire = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "TRANSPORT")
                r.transport = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "RESPONSABILITE")
                r.responsabilite = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "VEHICULE")
                r.vehicule = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "REPRESENTATION")
                r.representation = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "RISQUE")
                r.risque = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "EAU_ELEC")
                r.eau_elec = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "LOGEMENT")
                r.logement = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "SUP_LOGEMENT")
                r.sup_logement = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "GROSS")
                r.salaire_brut = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "SIT")
                r.sit = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "LOG_PAYE")
                r.log_paye = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "LOG_RETENU")
                r.log_retenu = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "VOITURE")
                r.voiture = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "EAU_ELEC_RET")
                r.eau_elec_ret = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "SBT")
                r.sbt = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "SC")
                r.sc = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "FP")
                r.fp = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "PVID")
                r.pvid = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "SNI")
                r.sni = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "SNI_AN")
                r.sni_an = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "BASE_IRPP")
                r.base_irpp = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "C1")
                r.c1 = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "C2")
                r.c2 = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "C3")
                r.c3 = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "C4")
                r.c4 = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "IRPP_AN")
                r.irpp_an = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "IRPP_MENSUEL")
                r.irpp_men = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "CAC")
                r.cac = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "CFC")
                r.cfc = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "RAV")
                r.rav = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "TDL")
                r.tdl = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "CNPS")
                r.cnps = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "RETENUES")
                r.retenues = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "NET")
                r.salaire_net = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "PVIDP")
                r.pvid_pat = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "CNPSP")
                r.cnps_pat = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "ACCTRAV")
                r.acctrav_pat = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "CFCP")
                r.cfc_pat = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "FNEP")
                r.fne_pat = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "RETENUES_PATRO")
                r.retenues_pat = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "AT")
                r.at = line_net[0].amount if line_net else 0.0

                line_net = lns.filtered(lambda x: x.code == "AF")
                r.af = line_net[0].amount if line_net else 0.0

    @api.multi
    def _compute_primes_grat(self):
        for r in self:
            r.primes_grat = 0.0
            if r.line_ids:
                line_brut = r.line_ids.filtered(lambda x: x.code == "GROSS")
                line_base = r.line_ids.filtered(lambda x: x.code == "BASIC")
                brut = line_brut[0].amount if line_brut else 0.0
                base = line_base[0].amount if line_base else 0.0
                r.primes_grat = brut - base

    @api.multi
    def action_payslip_done(self):
        for r in self:
            res = None
            if r.contract_id.type_id.generer_facture:
                r.compute_sheet()
                res = r.write({'state': 'done'})
            else:
                res = super(HrPayslip, self).action_payslip_done()
            return res

    @api.depends('employee_id', 'date_from')
    def compute_timesheet_data(self):
        for r in self:
            datas = r.compute_timesheet_hours(
                r.contract_id, r.date_from, r.date_to)
            r.total_hours = datas.get('total_hours') or 0.0
            r.timesheet_hours = datas.get('timesheet_hours') or 0.0
