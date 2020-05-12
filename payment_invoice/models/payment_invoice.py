from odoo import api, fields, models, exceptions
from odoo.exceptions import UserError

class PaymentInvoice(models.Model):
    _inherit = "account.payment"

    invoice_id = fields.Many2one('account.move', string='Facture à recouvrer', tracking=True)

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id and self.partner_type == "customer":
            invoice_id = self.env['account.move'].search([('partner_id', '=', self.partner_id), ('company_id', '=', self.env.company.id), ('state', '=', 'open'), ('type', '=', 'out_invoice')]).id
        
        else if self.partner_id and self.partner_type == "supplier":
            invoice_id = self.env['account.move'].search([('partner_id', '=', self.partner_id), ('company_id', '=', self.env.company.id), ('state', '=', 'open'), ('type', '=', 'in_invoice')]).id
        
        else:
            invoice_id = None