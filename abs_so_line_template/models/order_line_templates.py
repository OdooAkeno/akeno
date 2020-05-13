# -*- coding: utf-8 -*-
#################################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2019-today Ascetic Business Solution <www.asceticbs.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################
from odoo import api,fields,models,_

class OrderLineTemplates(models.Model):
    _name = "order.line.templates"
    _rec_name = "partner_id"

    partner_id = fields.Many2one('res.partner', string='Customer',help="This field display customer's name",required=True)
    product_id = fields.Many2one('product.product',string='Product',help="This field display product's name",required=True)
    product_description = fields.Char(string="Description",help="This field display product description")
    product_uom_qty = fields.Float(string="Ordered Quantity",default="1.0",help="This field display Ordered Quantity")
    price_unit = fields.Float(string="Unit Price",default="0.0",help="This field display Unit Price")
    tax_ids = fields.Many2many('account.tax',string="Tax",help="This field display different types of tax")
   
    # poduct_id_change function change the display product unit price and product description
    @api.multi
    @api.onchange('product_id')
    def product_id_channge(self):
        if self.product_id.description_sale and self.product_id.default_code:				 
            self.product_description = '[%s] %s' % (self.product_id.default_code,self.product_id.name) + self.product_id.description_sale
        elif self.product_id.description_sale:
            self.product_description = self.product_id.name + self.product_id.description_sale
        elif self.product_id.default_code:
            self.product_description = '[%s] %s' % (self.product_id.default_code,self.product_id.name) 	
        else:
            self.product_description = self.product_id.name
        self.price_unit = self.product_id.lst_price
	
	
