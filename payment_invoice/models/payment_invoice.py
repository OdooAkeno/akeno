from odoo import api, fields, models, exceptions
from odoo.exceptions import UserError

class PaymentInvoice(models.Model):
    _inherit = "account.payment"

    invoice_id = fields.Many2one('account.invoice',  string=u'Facture à recouvrer')

    @api.onchange('partner_id')
    def _onchange_invoice_id(self):

    	if self.partner_id:
    		return {'domain': {'invoice_id': [('partner_id', 'in', [self.partner_id.id])]}}

