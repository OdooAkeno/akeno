# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrPayslipRun(models.Model):

    _inherit = 'hr.payslip.run'

    total_salaire_net = fields.Float(
        string='Total salaire net',
        readonly=True,
        compute="_compute_total_salaire_net",
        digits=(16, 1))

    total_primes = fields.Float(
        string='Total primes et gratifications',
        readonly=True,
        compute="_compute_total_primes",
        digits=(16, 1))

    total_retenues = fields.Float(
        string='Total retenues',
        readonly=True,
        compute="_compute_total_retenues",
        digits=(16, 1))

    @api.multi
    def _compute_total_salaire_net(self):
        for r in self:
            r.total_salaire_net = 0.0
            if r.slip_ids:
                r.total_salaire_net = sum(r.slip_ids.mapped("salaire_net"))

    @api.multi
    def _compute_total_primes(self):
        for r in self:
            r.total_primes = 0.0
            if r.slip_ids:
                r.total_primes = sum(r.slip_ids.mapped("primes_grat"))

    @api.multi
    def _compute_total_retenues(self):
        for r in self:
            r.total_retenues = 0.0
            if r.slip_ids:
                r.total_retenues = sum(r.slip_ids.mapped("retenues"))

    @api.multi
    def close_payslip_run(self):
        self.slip_ids.filtered(
            lambda x: x.state == "draft").action_payslip_done()
        return super(HrPayslipRun, self).close_payslip_run()

    @api.multi
    def send_by_mail(self):
        pass
