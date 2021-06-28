# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError

class Sale_order_line_inherit(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('discount', 'product_uom_qty', 'price_unit')
    def _onchange_discount(self):
        if self.disc_flag == False:
            self.discount_amount = ((self.price_unit * self.product_uom_qty) / 100) * self.discount

        self.disc_flag = True

    @api.onchange('discount_amount')
    def _onchange_discount_amount(self):
        if ((self.price_unit * self.product_uom_qty) / 100) and self.disc_flag == False:
            self.discount = self.discount_amount / ((self.price_unit * self.product_uom_qty) / 100)
            self.discount_show = self.discount

        self.disc_flag = True

    @api.onchange('discount_show')
    def _onchange_discount_show(self):
        if self.disc_flag == False:
            self.discount_amount = ((self.price_unit * self.product_uom_qty) / 100) * self.discount_show
            self.discount = self.discount_show

        self.disc_flag = True

    discount_amount = fields.Float(string=_('Discount amount'), default=0.0, digits=(10,2))
    discount = fields.Float(string=_('Discount (%)'), digits=(2,6), default=0.0)
    discount_show = fields.Float(string=_('Discount (%)'), digits=(2,2), default=0.0)
    disc_flag = fields.Boolean()

    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        self.ensure_one()
        res = {}
        account = self.product_id.property_account_income_id or self.product_id.categ_id.property_account_income_categ_id

        if not account and self.product_id:
            raise UserError(_('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                (self.product_id.name, self.product_id.id, self.product_id.categ_id.name))

        fpos = self.order_id.fiscal_position_id or self.order_id.partner_id.property_account_position_id
        if fpos and account:
            account = fpos.map_account(account)

        res = {
            'name': self.name,
            'sequence': self.sequence,
            'origin': self.order_id.name,
            'account_id': account.id,
            'price_unit': self.price_unit,
            'quantity': qty,
            'discount': self.discount,
            'discount_amount': self.discount_amount,
            'discount_show': self.discount_show,
            'uom_id': self.product_uom.id,
            'product_id': self.product_id.id or False,
            'invoice_line_tax_ids': [(6, 0, self.tax_id.ids)],
            'account_analytic_id': self.order_id.analytic_account_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'display_type': self.display_type,
        }
        return res

class Account_invoice_line_inherit(models.Model):
    _inherit = 'account.invoice.line'

    @api.onchange('discount', 'quantity', 'price_unit')
    def _onchange_discount(self):
        if self.disc_flag == False:
            self.discount_amount = ((self.price_unit * self.quantity) / 100) * self.discount

        self.disc_flag = True

    @api.onchange('discount_amount')
    def _onchange_discount_amount(self):
        if ((self.price_unit * self.quantity) / 100) and self.disc_flag == False:
            self.discount = self.discount_amount / ((self.price_unit * self.quantity) / 100)
            self.discount_show = self.discount

        self.disc_flag = True

    @api.onchange('discount_show')
    def _onchange_discount_show(self):
        if self.disc_flag == False:
            self.discount_amount = ((self.price_unit * self.quantity) / 100) * self.discount_show
            self.discount = self.discount_show

        self.disc_flag = True

    discount_amount = fields.Float(string=_('Discount amount'), default=0.0, digits=(10,2))
    discount = fields.Float(string=_('Discount (%)'), digits=(2,6), default=0.0)
    discount_show = fields.Float(string=_('Discount (%)'), digits=(2,2), default=0.0)
    disc_flag = fields.Boolean()

    def _prepare_invoice_line(self):
        data = {
            'name': self.name,
            'origin': self.origin,
            'uom_id': self.uom_id.id,
            'product_id': self.product_id.id,
            'account_id': self.account_id.id,
            'price_unit': self.price_unit,
            'quantity': self.quantity,
            'discount': self.discount,
            'discount_amount': self.discount_amount,
            'discount_show': self.discount_show,
            'account_analytic_id': self.account_analytic_id.id,
            'analytic_tag_ids': self.analytic_tag_ids.ids,
            'invoice_line_tax_ids': self.invoice_line_tax_ids.ids
        }
        return data

class Sale_order_inherit(models.Model):
    _inherit = 'sale.order'

    discount = fields.Monetary(string=_('Discount'), default=0.0, store=True, readonly=True,
                               compute='_compute_discount', currency_field='currency_id')
    amount_without_discount_tax = fields.Monetary(string=_('Amount without discount and tax'), default=0.0, store=True,
                                                  readonly=True, compute='_compute_amount_without_discount_tax',
                                                  currency_field='currency_id')

    @api.one
    @api.depends('order_line.discount_amount')
    def _compute_discount(self):
        disc = 0

        for line in self.order_line:
            if line.discount_amount:
                disc += line.discount_amount

        self.discount = disc

    @api.one
    @api.depends('order_line.discount_amount', 'amount_untaxed')
    def _compute_amount_without_discount_tax(self):
        disc = 0

        for line in self.order_line:
            if line.discount_amount:
                disc += line.discount_amount

        self.amount_without_discount_tax = self.amount_untaxed + disc

class Account_invoice_inherit(models.Model):
    _inherit = 'account.invoice'

    discount = fields.Monetary(string=_('Discount'), default=0.0, store=True, readonly=True,
                               compute='_compute_discount', currency_field='currency_id')
    amount_without_discount_tax = fields.Monetary(string=_('Amount without discount and tax'), default=0.0, store=True,
                                                  readonly=True, compute='_compute_amount_without_discount_tax',
                                                  currency_field='currency_id')

    @api.one
    @api.depends('invoice_line_ids.discount_amount')
    def _compute_discount(self):
        disc = 0

        for line in self.invoice_line_ids:
            if line.discount_amount:
                disc += line.discount_amount

        self.discount = disc

    @api.one
    @api.depends('invoice_line_ids.discount_amount', 'amount_untaxed')
    def _compute_amount_without_discount_tax(self):
        disc = 0

        for line in self.invoice_line_ids:
            if line.discount_amount:
                disc += line.discount_amount

        self.amount_without_discount_tax = self.amount_untaxed + disc