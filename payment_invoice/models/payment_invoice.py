from odoo import api, fields, models, exceptions
from odoo.exceptions import UserError

class PaymentInvoice(models.Model):
    _inherit = "account.payment"

    invoice_id = fields.Many2one('account.invoice', string='Facture à recouvrer')

    @api.onchange('partner_id')
    def _computer_invoice(self):

        for p in self:
            if p.partner_id and p.partner_type == "customer":
                invoice_id = self.env['account.invoice'].search([('partner_id', '=', p.partner_id.id), ('state', '=', 'open'), ('type', '=', 'out_invoice')])
            
            elif p.partner_id and p.partner_type == "supplier":
                invoice_id = self.env['account.invoice'].search([('partner_id', '=', p.partner_id.id), ('state', '=', 'open'), ('type', '=', 'in_invoice')])
            
            else:
                invoice_id = None