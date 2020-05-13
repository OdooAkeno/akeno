from odoo import api, fields, models, exceptions
from odoo.exceptions import UserError

class PaymentInvoice(models.Model):
    _inherit = "account.payment"

    invoice_id = fields.Many2one('account.invoice',  string=u'Facture à recouvrer')

    @api.onchange('partner_id')
    def _onchange_invoice_id(self):

    	if self.partner_id:
    		if self.payment_type == "inbound":
    			return {'domain': {'invoice_id': [('partner_id', 'in', [self.partner_id.id]), ('type', '=', "out_invoice" ), ('state', '=', 'open')] }}

    		if self.payment_type == "outbound":
    			return {'domain': {'invoice_id': [('partner_id', 'in', [self.partner_id.id]), ('type', '=', "in_invoice" ), ('state', '=', 'open')] }}