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

class SaleOrder(models.Model):
    _inherit="sale.order"

    sales_order_line_template = fields.Boolean(string='Sales Order Line Template',help="This fielda allows to add order line template in sale order")

    ''' if checkbox "Use Sales Order Line Template" is True then according customer find order_line records from order.line.templates and display in sale.order form '''
    @api.model
    def create(self,vals):
        result = super(SaleOrder,self).create(vals)

        if vals['sales_order_line_template'] == True:
            if self.env['order.line.templates'].search([('partner_id','=',vals['partner_id'])]):
                template_ids = self.env['order.line.templates'].search([('partner_id','=',vals['partner_id'])])
                for temp_record in template_ids:
                    p_id = temp_record.product_id.id
                    p_desc = temp_record.product_description
                    p_uom_qty = temp_record.product_uom_qty
                    p_price_qty = temp_record.price_unit
                    p_tax_id = temp_record.tax_ids
                    p_tax_id_list = [] 
                    for record_tax_id in p_tax_id:
                        p_tax_id_list.append(record_tax_id.id)
                    orderlineTemplate = {"product_id":p_id,
                                        "name":p_desc,
                                        "product_uom_qty":p_uom_qty,
                                        "price_unit":p_price_qty,
                                        "tax_id":[(6,0,p_tax_id_list)],
                                        "order_id":result.id,
                                        }
                    self.env['sale.order.line'].create(orderlineTemplate)
        return result

