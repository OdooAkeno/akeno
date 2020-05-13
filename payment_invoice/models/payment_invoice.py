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
    	else:
    		if self.payment_type == "inbound":
    			return {'domain': {'invoice_id': [('type', '=', "out_invoice" ), ('state', '=', 'open')] }}

    		if self.payment_type == "outbound":
    			return {'domain': {'invoice_id': [('type', '=', "in_invoice" ), ('state', '=', 'open')] }}


class AccountInvoice(models.Model):
	
	_inherit = "account.invoice"
	
	payment_id = fields.Many2one('account.payment',  string=u'Paiement effectué')

	@api.multi
	def _compute_payments_widget_to_reconcile_info(self):

		res=super(AccountInvoice,self)._compute_payments_widget_to_reconcile_info()
			for invoice in self:

				if invoice.type = "out_invoice":
                	domain.extend([(self.payment_id.invoice_id, '=', self.id)])
            	if invoice.type = "in_invoice":
                	domain.extend([(self.payment_id.invoice_id, '=', self.id)])
		return res
