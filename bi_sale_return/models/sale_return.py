# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_compare
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import formatLang
from datetime import datetime
from odoo.addons import decimal_precision as dp


_logger = logging.getLogger(__name__)
class BiSaleReturn(models.Model):
    _name = 'bi.sale.return'
    _description = 'Sale Return'

    @api.depends('return_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.return_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.depends('company_id')
    def _compute_location(self):
        for order in self:
            order.location_id = False
            order.picking_type_id = False
            if order.company_id:
                location_id = self.env['stock.location'].search([('company_id', '=', order.company_id.id), ('usage', '=', 'internal'), ('barcode', '=', 'ZBV')])
                if location_id:
                    order.location_id = location_id
                    type_obj = self.env['stock.picking.type'].search([
                        ('default_location_dest_id', '=', order.location_id.id),
                        ('code', '=', 'incoming'), ('barcode', '=', 'WH-RECEIPTS-BV')
                    ])
                    if type_obj:
                        order.picking_type_id = type_obj.id

    name = fields.Char('Reference du retour', required=True, index=True, copy=False, default='Nouveau')
    origin = fields.Char('Source Document', copy=False)
    date_order = fields.Date(string='Date de retour', default=fields.Date.today())
    date_approve = fields.Date(string="Date de validation")
    partner_id = fields.Many2one('res.partner', string='Client')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('return', 'Retour consigne'),
        ('cancel', 'Annulé')
    ], string='Statut', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    return_line = fields.One2many('bi.sale.return.line', 'return_id', string='Lignes ', copy=True)
    amount_untaxed = fields.Monetary(string='Montant hors taxe', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    picking_type_id = fields.Many2one('stock.picking.type', 'Type operation', required=True, compute='_compute_location')
    default_location_dest_id_usage = fields.Selection(related='picking_type_id.default_location_dest_id.usage', string='Emplacement de destination', readonly=True)
    is_delivered = fields.Boolean(string="Is Delivered?", default=False, copy=False)
    user_id = fields.Many2one('res.users', string='Responsable du retour', default=lambda self: self.env.user.id)
    location_id = fields.Many2one('stock.location', string='Emplacement', required=True, compute='_compute_location')
    picking_id = fields.Many2one('stock.picking', string='Livraison', copy=False)
    invoice_id = fields.Many2one('account.invoice', string='Facture', copy=False)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id)

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nouveau')) == _('Nouveau'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('bi.sale.return') or _('Nouveau')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('bi.sale.return') or _('Nouveau')
        return super(BiSaleReturn, self).create(vals)

    @api.multi
    def unlink(self):
        for so_return in self:
            if so_return.state == 'return' and so_return.is_delivered and so_return.invoice_id:
                raise UserError(_('Vous ne pouvez pas supprimer cet enregistrement car le bon de livraison et la facture ont déjà été créés.'))
            so_return.return_line.unlink()
        return super(BiSaleReturn, self).unlink()

    @api.multi
    def approve_return(self):
        self.state = 'return'

    @api.multi
    def cancel_return(self):
        self.state = 'cancel'

    @api.multi
    def send_return_products(self):
        if not self.picking_id:
            picking = self.env['stock.picking']
            location_src_id, vendorloc = self.env['stock.warehouse']._get_partner_locations()
            picking_values = {
                'partner_id': self.partner_id.id,
                'picking_type_id': self.picking_type_id.id,
                'move_type': 'direct',
                'location_id': location_src_id.id,
                'location_dest_id': self.picking_type_id.default_location_dest_id.id,
                'scheduled_date': datetime.now(),
                'origin': self.name + str(datetime.now()),
            }
            picking_id = picking.create(picking_values)
            self.write({'picking_id': picking_id.id})
            for line in self.return_line:
                move_values = {
                    'picking_id': picking_id.id,
                    'name': line.name,
                    'company_id': self.picking_type_id.default_location_dest_id.company_id.id,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom.id,
                    'product_uom_qty': line.product_qty,
                    'partner_id': self.partner_id.id,
                    'location_id': location_src_id.id,
                    'location_dest_id': self.picking_type_id.default_location_dest_id.id,
                    'rule_id': 1,
                    'procure_method': 'make_to_stock',
                    'origin': self.name + str(datetime.now()),
                    'picking_type_id': self.picking_type_id.id,
                    'warehouse_id': self.picking_type_id.warehouse_id.id,
                    'date': datetime.now(),
                    'date_expected': datetime.now(),
                    'propagate': True,
                    'priority': '1',
                }
                self.env['stock.move'].sudo().create(move_values)
            picking_id.action_confirm()
            picking_id.action_assign()
            self.is_delivered = True
            return {
                'name': _("Delivery"),
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'stock.picking',
                'view_id': self.env.ref('stock.view_picking_form').id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'current',
                'res_id': picking_id.id,
            }

    @api.multi
    def create_refund(self):
        if not self.picking_id:
            raise UserError("Retournez d'abord les produits!")
        if not self.invoice_id:
            tax_details = []
            invoice_values = {
                'partner_id': self.partner_id.id,
                'date_invoice': datetime.now().date(),
                'date_due': datetime.now().date(),
                'user_id': self.user_id.id,
                'journal_id': 2,
                'account_id': self.partner_id.property_account_receivable_id.id,
                'date': datetime.now().date(),
                'type': 'out_refund',
            }
            invoice_id = self.env['account.invoice'].create(invoice_values)
            for each_line in self.return_line:
                if each_line.product_id.property_account_income_id:
                    line_account_id = each_line.product_id.property_account_income_id.id
                else:
                    line_account_id = each_line.product_id.categ_id.property_account_income_categ_id.id
                line_values = {
                    'invoice_id': invoice_id.id,
                    'product_id': each_line.product_id.id,
                    'name': each_line.name,
                    'account_id': line_account_id,
                    'quantity': each_line.product_qty,
                    'uom_id': each_line.product_uom.id,
                    'price_unit': each_line.price_unit,
                    'invoice_line_tax_ids': [(6, 0, each_line.product_id.taxes_id.ids)],
                }
                self.env['account.invoice.line'].create(line_values)
                if self.amount_tax > 0:
                    existing_tax_id = self.env['account.invoice.tax'].search([
                        ('account_id', '=', line_account_id),
                        ('name', '=', each_line.tax_ids.name),
                        ('invoice_id', '=', invoice_id.id)
                    ], limit=1)
                    if existing_tax_id:
                        existing_tax_id.base = existing_tax_id.base + each_line.price_subtotal
                        existing_tax_id.amount = existing_tax_id.amount + each_line.price_tax
                    else:
                        tax_values = {
                            'invoice_id': invoice_id.id,
                            'name': each_line.tax_ids.name,
                            'tax_id': each_line.tax_ids.id,
                            'account_id': line_account_id,
                            'base': each_line.price_subtotal,
                            'amount': each_line.price_tax,
                            'currency_id': each_line.currency_id.id
                        }
                        self.env['account.invoice.tax'].create(tax_values)
            self.invoice_id = invoice_id.id
            return {
                'name': _("Credit Note"),
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'account.invoice',
                'view_id': self.env.ref('account.invoice_form').id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'current',
                'res_id': invoice_id.id,
            }


class BiSaleReturnLine(models.Model):
    _name = 'bi.sale.return.line'
    _description = 'Sale Return Line'

    name = fields.Text(string='Description', required=True)
    product_qty = fields.Float(string='Quantité', digits=dp.get_precision('Product Unit of Measure'), required=True)
    tax_ids = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    product_uom = fields.Many2one('uom.uom', string='Unité de mesure', required=True)
    product_id = fields.Many2one('product.product', string='Article', domain=[('sale_ok', '=', True), ('default_code', 'in', ['BV_12.5', 'CONS_12.5'])], change_default=True, required=True)
    price_unit = fields.Float(string='Prix unitaire', required=True, digits=dp.get_precision('Product Price'))
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Sous total', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Taxe', store=True)
    return_id = fields.Many2one('bi.sale.return', string='Reference de commande', index=True, required=True, ondelete='cascade')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Compte analytique')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Etiquette analytique')
    state = fields.Selection(related='return_id.state', store=True, readonly=False)
    currency_id = fields.Many2one(related='return_id.currency_id', store=True, string='Devise', readonly=True)
    partner_id = fields.Many2one('res.partner', related='return_id.partner_id', string='Partenaire', readonly=True, store=True)
    date_order = fields.Date(related='return_id.date_order', string='Date de commande', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', related='return_id.company_id', store=True)

    @api.depends('product_qty', 'price_unit', 'tax_ids')
    def _compute_amount(self):
        for line in self:
            vals = line._prepare_compute_all_values()
            taxes = line.tax_ids.compute_all(
                vals['price_unit'],
                vals['currency_id'],
                vals['product_qty'],
                vals['product'],
                vals['partner'])
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    def _prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        return {
            'price_unit': self.price_unit,
            'currency_id': self.return_id.currency_id,
            'product_qty': self.product_qty,
            'product': self.product_id,
            'partner': self.return_id.partner_id,
        }

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.price_unit = self.product_qty = 0.0
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

        product_lang = self.product_id.with_context(
            lang=self.partner_id.lang,
            partner_id=self.partner_id.id,
        )
        self.name = product_lang.display_name
        if product_lang.description_sale:
            self.name += '\n' + product_lang.description_sale

        if self.product_id:
            if self.product_id.taxes_id:
                self.tax_ids = [(6, 0, self.product_id.taxes_id.ids)]
            self.price_unit = self.product_id.standard_price
        return result
