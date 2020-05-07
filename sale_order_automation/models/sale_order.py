from odoo import api, fields, models, exceptions
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    date_generate_invoice = fields.Date("Date de la derniere facturation", compute='creation_et_validation_facture', store=True)
    @api.multi
    def action_confirm(self):
        imediate_obj=self.env['stock.immediate.transfer']
        res=super(SaleOrder,self).action_confirm()
        for order in self:

            warehouse=order.warehouse_id
            if warehouse.is_delivery_set_to_done and order.picking_ids: 
                for picking in self.picking_ids:
                    picking.action_confirm()
                    picking.action_assign()


                    #imediate_rec = imediate_obj.create({'pick_ids': [(4, order.picking_ids.id)]})
                    #imediate_rec.process()
                    if picking.state !='done':
                        for move in picking.move_ids_without_package:
                            move.quantity_done = move.product_uom_qty
                        #picking.button_validate()

            #self._cr.commit()

        return res  

    @api.multi        
    @api.depends('order_line.qty_delivered')
    def creation_et_validation_facture(self):
        for order in self:

            warehouse=order.warehouse_id
            pickings = order.picking_ids.filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')

            if warehouse.create_invoice and pickings:
                for picking in pickings:
                    picking.carried_id.id = None

                order.sudo().action_invoice_create() 

            if warehouse.validate_invoice and order.invoice_ids:
                for invoice in order.invoice_ids:
                    invoice.sudo().action_invoice_open()

            dates_list = [date for date in pickings.mapped('date_done') if date]
            order.date_generate_invoice = min(dates_list).date() if dates_list else False
