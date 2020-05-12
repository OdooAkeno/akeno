from odoo import api, fields, models, exceptions
from odoo.exceptions import UserError

class PaymentInvoice(models.Model):
    _inherit = "account.payment"

    invoice_id = fields.Many2one(comodel_name='account.invoice', string='Facture à recouvrer', domain="[('state', '=', 'open'), ('type', '=', 'out_invoice')]")

    @api.onchange('partner_id')
    def _computer_invoice(self):

        if self.partner_id and self.partner_type == "customer":
            self.invoice_id = self.env['account.invoice'].search([('partner_id', '=', self.partner_id.id)])
            
        elif p.partner_id and p.partner_type == "supplier":
            self.invoice_id = self.env['account.invoice'].search([('partner_id', '=', self.partner_id.id)])
            
        else:
            self.invoice_id = None