from odoo import api, fields, models, exceptions
from odoo.exceptions import UserError

class PaymentInvoice(models.Model):
    _inherit = "account.payment"

    invoice_ids = fields.Many2many('account.invoice', 'account_invoice_payment_rel', 'payment_id', 'invoice_id', string="Invoices", required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, help="""Technical field containing the invoices for which the payment has been generated.
                                                                                                                                                                       This does not especially correspond to the invoices reconciled with the payment,
                                                                                                                                                                       as it can have been generated first, and reconciled later""")

    @api.onchange('partner_id')
    def _onchange_invoice_id(self):

    	if self.partner_id:
    		if self.payment_type == "inbound":
    			return {'domain': {'invoice_ids': [('partner_id', 'in', [self.partner_id.id]), ('type', '=', "out_invoice" ), ('state', '=', 'open')] }}

    		if self.payment_type == "outbound":
    			return {'domain': {'invoice_ids': [('partner_id', 'in', [self.partner_id.id]), ('type', '=', "in_invoice" ), ('state', '=', 'open')] }}
    	else:
    		if self.payment_type == "inbound":
    			return {'domain': {'invoice_ids': [('type', '=', "none" ), ('state', '=', 'none')] }}

    		if self.payment_type == "outbound":
    			return {'domain': {'invoice_ids': [('type', '=', "none" ), ('state', '=', 'none')] }}
