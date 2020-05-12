from odoo import api, fields, models, exceptions
from odoo.exceptions import UserError

class PaymentInvoice(models.Model):
    _inherit = "account.payment"

    invoice_id = fields.Many2one('account.invoice', string='Facture à recouvrer', store=True, compute='_computer_partner')

    @api.onchange('partner_id')
    def _computer_partner(self):
        if self.partner_id and self.partner_type == "customer":
            invoice_id = self.env['account.invoice'].search([('partner_id', '=', self.partner_id.id), ('state', '=', 'open'), ('type', '=', 'out_invoice')]).id
        
        elif self.partner_id and self.partner_type == "supplier":
            invoice_id = self.env['account.invoice'].search([('partner_id', '=', self.partner_id.id), ('state', '=', 'open'), ('type', '=', 'in_invoice')]).id
        
        else:
            invoice_id = None