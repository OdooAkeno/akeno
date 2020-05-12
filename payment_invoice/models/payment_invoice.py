from odoo import api, fields, models, exceptions
from odoo.exceptions import UserError

class PaymentInvoice(models.Model):
    _inherit = "account.payment"

    invoice_id = fields.Many2one('account.invoice', string=u'Facture à recouvrer', track_visibility='onchange', compute='_computer_invoice', readonly=True)

    @api.onchange('partner_id')
    def _computer_invoice(self):

        if self.partner_id and self.partner_type == "customer":
            self.invoice_id = self.env['account.invoice'].search(['&','&', ('partner_id', '=', self.partner_id.id), ('state', '=', 'open'), ('type', '=', 'out_invoice')]).id
            
        elif self.partner_id and self.partner_type == "supplier":
            self.invoice_id = self.env['account.invoice'].search(['&','&', ('partner_id', '=', self.partner_id.id), ('state', '=', 'open'), ('type', '=', 'out_invoice')]).id
            
        else:
            self.invoice_id = None