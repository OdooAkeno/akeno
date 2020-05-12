# -*- coding: utf-8 -*-

from openerp import models, fields, api, tools, _
from odoo.exceptions import UserError

class PaymentDistribution(models.TransientModel):
    _name = 'payment.distribution'
    _description = 'Payment Distribution'

    @api.model
    def _default_journal(self):
        journal = self.env['account.journal'].search([('type', 'in', ['bank', 'cash'])], limit=1)
        return journal.id if journal else False

    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    payment_date = fields.Date("Payment Date", default=fields.Date.context_today)
    reference = fields.Char('Memo') 
    payment_amount = fields.Monetary(string='Payment Amount', required=True)
    invoice_type = fields.Selection([('invoice', 'Customer Invoices'), ('bills','Vendor Bills'),
    ('credit_note', 'Vendor Credit Notes'), ('debit_note', 'Customer Credit Notes')], required=True, string='Invoice Type', default='invoice')
    distribution_line_ids = fields.One2many('payment.distribution.line', 'distribution_id', string='Partial Inovice Line')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, domain=[('type', 'in', ['cash', 'bank'])], default=_default_journal)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)

    @api.onchange('partner_id', 'invoice_type')
    def onchange_partner(self):
        if self.partner_id:
            self.get_partner_invoices()

    def get_partner_invoices(self):
        invoices = []
        res = {'invoice': 'out_invoice', 'bills': 'in_invoice', 'credit_note': 'in_refund', 'debit_note': 'out_refund'}
        domain = [('type', '=', res[self.invoice_type]), ('state', '=', 'open'), ('partner_id', '=', self.partner_id.id)]
        invoice_ids = self.env['account.invoice'].search(domain)
        for inv in invoice_ids:
            invoices.append({
                'partner_id': inv.partner_id.id,
                'date_invoice': inv.date_invoice,
                'residual': inv.residual,
                'invoice_total' : inv.amount_total,
                'invoice_id': inv.id,
                'currency_id': inv.currency_id and inv.currency_id.id or False
            })
        self.distribution_line_ids = [(0, 0, inv) for inv in invoices]

    def _check_valid_payment(self):
        if self.payment_amount < sum(self.distribution_line_ids.mapped('amount_to_pay')):
            raise UserError(_("Total amount of lines can't be greater than payment amount !"))
        if self.distribution_line_ids.filtered(lambda x: x.residual < x.amount_to_pay):
            raise UserError(_("allocated amount must be less than or equal to amount to pay !"))
        if self.distribution_line_ids.filtered(lambda x: x.currency_id != self.journal_id.company_id.currency_id):
            raise UserError(_("Journal and invoices must have same currency !"))        

    def make_payment_distribution(self):
        self.ensure_one()
        payment_vals = {}
        move_lines = self.env['account.move.line']
        self._check_valid_payment()
        vals = {'invoice': {'payment_type': 'inbound', 'partner_type': 'customer'},
                'bills': {'payment_type': 'outbound', 'partner_type': 'supplier'},
                'credit_note':{'payment_type': 'inbound', 'partner_type': 'supplier'},
                'debit_note': {'payment_type': 'outbound', 'partner_type': 'customer'}}
        payment_vals.update(vals[self.invoice_type])
        payment_vals.update({
            'partner_id': self.partner_id and self.partner_id.id or False,
            'journal_id': self.journal_id and self.journal_id.id or False,
            'payment_date': self.payment_date or self.Date.context_today(self),
            'communication': self.reference or '',
            'amount': self.payment_amount,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in') and self.env.ref('account.account_payment_method_manual_in').id
             if self.invoice_type in ['invoice', 'credit_note'] else self.env.ref('account.account_payment_method_manual_out') and self.env.ref('account.account_payment_method_manual_out').id
        })
        payment = self.env['account.payment'].create(payment_vals)
        if payment:
            self.distribution_line_ids.write({'payment_id': payment.id})
            payment.post()
        lines_to_reconcile = self.distribution_line_ids.filtered(lambda x: x.payment_id)
        if not lines_to_reconcile or payment.state != 'posted':
            raise UserError(_("Either payment not created or confirmed !"))
        for line in lines_to_reconcile.filtered(lambda x:x.amount_to_pay > 0):
            invoice_move = line.invoice_id.move_id.line_ids.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
            payment_move = line.payment_id.move_line_ids.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
            move_lines |= (invoice_move + payment_move) 
            if line.currency_id and invoice_move and payment_move:
                rate = line.currency_id.with_context(date=invoice_move.date).rate
                amount_reconcile_currency = line.currency_id.round(line.amount_to_pay * rate)
                self.env['account.partial.reconcile'].create({
                    'debit_move_id': invoice_move.id,
                    'credit_move_id': payment_move.id,
                    'amount': line.amount_to_pay,
                    'amount_currency': amount_reconcile_currency,
                    'currency_id': line.currency_id.id,
                })
        move_lines.auto_reconcile_lines()

class PaymentDistributionLine(models.TransientModel):
    _name = 'payment.distribution.line'
    _description = 'Payment Distribution Line'

    distribution_id = fields.Many2one('payment.distribution', 'Distribution Wizard')
    amount_to_pay = fields.Monetary(string='Amount', required=True, default=0.0)
    date_invoice = fields.Date(string='Invoice Date', readonly=True)
    invoice_total = fields.Monetary(string='Invoice Total', readonly=True)
    residual = fields.Monetary(string='Amount Due', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    payment_id = fields.Many2one('account.payment', string="Payment", readonly=True)
    invoice_id = fields.Many2one('account.invoice', string="Invoice", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)

