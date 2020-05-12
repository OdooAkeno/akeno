from odoo import api, fields, models, exceptions
from odoo.exceptions import UserError

class PaymentInvoice(models.Model):
    _inherit = "account.payment"

    invoice_id = fields.One2many('account.invoice', related='partner_id.invoice_ids', string=u'Facture à recouvrer', store=True)