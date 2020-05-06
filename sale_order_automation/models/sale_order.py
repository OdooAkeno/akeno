from odoo import api, fields, models, exceptions
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    picking_ids = fields.One2many('stock.picking', 'sale_id', string='Transfers')
    effective_date = fields.Date("Effective Date", compute='_compute_effective_date', store=True, help="Completion date of the first delivery order.")

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


    @api.depends('picking_ids.date_done')
    def _compute_effective_date(self):
        for order in self:
            warehouse=order.warehouse_id
            pickings = order.picking_ids.filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')
            dates_list = [date for date in pickings.mapped('date_done') if date]
            order.effective_date = min(dates_list).date() if dates_list else False

            if warehouse.create_invoice and not order.invoice_ids:
                order.action_invoice_create()  
            if warehouse.validate_invoice and order.invoice_ids:
                for invoice in order.invoice_ids:
                    invoice.action_invoice_open()
