# -*- coding: utf-8 -*-

from odoo import models, fields, api,exceptions
from lxml import etree

class ProductProduct(models.Model):
    _inherit = "product.template"

    product_default = fields.Boolean(string=u'Produit Gaz ?', default=False)
    gaz = fields.Boolean(string=u'Gaz', default=False)
    consignation_12 = fields.Boolean(string=u'Consignation 12,5 kg ?', default=False)
    consignation_25 = fields.Boolean(string=u'Consignation 25 kg ?', default=False)
    deconsignation_12 = fields.Boolean(string=u'Deconsignation 12,5 kg ?', default=False)
    deconsignation_25 = fields.Boolean(string=u'Deconsignation 25 kg ?', default=False)


ProductProduct()




class AccountMove(models.Model):
    _inherit = "account.move"

    type_b = fields.Selection([('12,5 kg', '12,5 kg'),
                               ('25 kg', '25 kg'),
                               ], 'Type de Bouteille',default='', required=True)

    quantity_gaz = fields.Float(string='Quantité Consignation',required=True)
    quantity_decon = fields.Float(string='Quantité Déconsignation')

    def _check_balanced(self):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        moves = self.filtered(lambda move: move.line_ids)
        if not moves:
            return

        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend of computed stored fields (e.g. balance).
        # It happens as the ORM makes the create with the 'no_recompute' statement.
        self.env['account.move.line'].flush(['debit', 'credit', 'move_id'])
        self.env['account.move'].flush(['journal_id'])
        self._cr.execute('''
            SELECT line.move_id, ROUND(SUM(line.debit - line.credit), currency.decimal_places)
            FROM account_move_line line
            JOIN account_move move ON move.id = line.move_id
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_company company ON company.id = journal.company_id
            JOIN res_currency currency ON currency.id = company.currency_id
            WHERE line.move_id IN %s
            GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(line.debit - line.credit), currency.decimal_places) != 0.0;
        ''', [tuple(self.ids)])

        query_res = self._cr.fetchall()
        if query_res:
            ids = [res[0] for res in query_res]
            sums = [res[1] for res in query_res]
            return
            



    @api.onchange('quantity_gaz','type_b','quantity_decon')
    def _onchange_partner(self):
        if self.partner_id and self.type_b:
            # lines = [(5, 0, 0)]
            lines = [(5, 0, 0)]
            # consign = self.env['product.template'].search([('product_default','=',True)])

            if self.type_b == '12,5 kg':
                # recuperer la consignation
                consign = self.env['product.template'].search([('product_default','=',True),('consignation_12','=',True)])
                if consign:
                    # move_id
                    vals1 = {
                        'product_id': consign[0].id,
                        'account_id':self.journal_id.default_credit_account_id.id,
                        'move_id':self.journal_id.default_credit_account_id.id,
                        'price_unit': consign[0].list_price,
                        'name': consign[0].name,
                        'product_uom_id': consign[0].uom_id.id,
                        'quantity': self.quantity_gaz,
                        'price_subtotal':consign[0].list_price * self.quantity_gaz,
                        'company_id': consign[0].company_id.id,
                        'discount': 0.0
                    }
                    lines.append((0,0,vals1))
                else:
                    msg = u"Erreur! Configurez la consignation de 12,5 kg !!"
                    raise exceptions.ValidationError(msg)
                    

                # recuperer le gaz
                gaz = self.env['product.template'].search([('product_default','=',True),('gaz','=',True)])
                if gaz:
                    type_b = float()
                    if self.type_b == '12,5 kg':
                        type_b = 12.5
                    else:
                        type_b = 25
                    vals3 = {
                        'product_id': gaz[0].id,
                        'account_id':self.journal_id.default_credit_account_id.id,
                        'move_id':self.journal_id.default_credit_account_id.id,
                        'price_unit': gaz[0].list_price,
                        'name': gaz[0].name,
                        'product_uom_id': gaz[0].uom_id.id,
                        'quantity': self.quantity_gaz * type_b,
                        'price_subtotal':consign[0].list_price * self.quantity_gaz,
                        'company_id': gaz[0].company_id.id,
                        'discount': 0.0
                    }
                    lines.append((0,0,vals3))
                else:
                    msg = u"Erreur! Configurez le gaz !!"
                    raise exceptions.ValidationError(msg)

                # recuperer la deconsignation
                deconsign = self.env['product.template'].search([('product_default','=',True),('deconsignation_12','=',True)])
                if deconsign:
                    vals2 = {
                        'product_id': deconsign[0].id,
                        'account_id':self.journal_id.default_credit_account_id.id,
                        'move_id':self.journal_id.default_credit_account_id.id,
                        'price_unit': deconsign[0].list_price,
                        'name': deconsign[0].name,
                        'product_uom_id': deconsign[0].uom_id.id,
                        'quantity': self.quantity_decon,
                        'price_subtotal':consign[0].list_price * self.quantity_decon,
                        'company_id': deconsign[0].company_id.id,
                        'discount': 0.0
                    }
                    lines.append((0,0,vals2))
                else:
                    msg = u"Erreur! Configurez la déconsignation de 12,5 kg !!"
                    raise exceptions.ValidationError(msg)
                

                self.invoice_line_ids = lines
                print("======> ",self.line_ids)

            elif self.type_b == '25 kg':
                # recuperer la consignation
                consign = self.env['product.template'].search([('product_default','=',True),('consignation_25','=',True)])
                if consign:
                    vals1 = {
                        'product_id': consign[0].id,
                        'account_id':self.journal_id.default_credit_account_id.id,
                        'move_id':self.journal_id.default_credit_account_id.id,
                        'price_unit': consign[0].list_price,
                        'name': consign[0].name,
                        'product_uom_id': consign[0].uom_id.id,
                        'quantity': self.quantity_gaz,
                        'price_subtotal':consign[0].list_price * self.quantity_gaz,
                        'company_id': consign[0].company_id.id,
                        'discount': 0.0
                    }
                    lines.append((0,0,vals1))
                else:
                    msg = u"Erreur! Configurez la consignation de 25 kg !!"
                    raise exceptions.ValidationError(msg)

                # recuperer le gaz
                gaz = self.env['product.template'].search([('product_default','=',True),('product_default','=',True)])
                if gaz:
                    type_b = float()
                    if self.type_b == '12,5 kg':
                        type_b = 12.5
                    else:
                        type_b = 25
                    vals3 = {
                        'product_id': gaz[0].id,
                        'account_id':self.journal_id.default_credit_account_id.id,
                        'move_id':self.journal_id.default_credit_account_id.id,
                        'price_unit': gaz[0].list_price,
                        'name': gaz[0].name,
                        'product_uom_id': gaz[0].uom_id.id,
                        'quantity': self.quantity_gaz * type_b,
                        'price_subtotal':consign[0].list_price * self.quantity_gaz,
                        'company_id': gaz[0].company_id.id,
                        'discount': 0.0
                    }
                    lines.append((0,0,vals3))
                else:
                    msg = u"Erreur! Configurez le gaz !!"
                    raise exceptions.ValidationError(msg)


                # recuperer la deconsignation
                deconsign = self.env['product.template'].search([('product_default','=',True),('deconsignation_25','=',True)])
                if deconsign:
                    vals2 = {
                        'product_id': deconsign[0].id,
                        'account_id':self.journal_id.default_credit_account_id.id,
                        'move_id':self.journal_id.default_credit_account_id.id,
                        'price_unit': deconsign[0].list_price,
                        'name': deconsign[0].name,
                        'product_uom_id': deconsign[0].uom_id.id,
                        'quantity': self.quantity_decon,
                        'price_subtotal':consign[0].list_price * self.quantity_decon,
                        'company_id': deconsign[0].company_id.id,
                        'discount': 0.0
                    }
                    lines.append((0,0,vals2))
                else:
                    msg = u"Erreur! Configurez la déconsignation de 12,5 kg !!"
                    raise exceptions.ValidationError(msg)

                self.invoice_line_ids = lines
                print("======> ",self.line_ids)
        else:
            if not self.type_b:
                msg = u"Erreur! selectionnez le type de bouteille"
                raise exceptions.ValidationError(msg)
            elif not self.partner_id:
                msg = u"Erreur! selectionnez le client"
                raise exceptions.ValidationError(msg)



AccountMove()





# discount
# invoice_line_tax_ids


# @api.onchange('type_b')
#     def _onchange_partner(self):
#         if self.partner_id:
#             if self.type_b == '12,5 kg':
#                 # recuperer la consignation
#                 consign = self.env['product.template'].search([('product_default','=',True)])
#                 # recuperer la deconsignation
#                 deconsign = self.env['product.template'].search([('product_default','=',True)])
#                 # recuperer le gaz
#                 gaz = self.env['product.template'].search([('product_default','=',True)])
#                 # products = self.env['product.template'].search([('product_default','=',True)])
#                 lines = [(5, 0, 0)]
#                 # for p in products:
#                 #     vals = {
#                 #         'product_id': p.id
#                 #         # 'quantity'
#                 #         # 'uom_id'
#                 #         # 'price_unit'
#                 #     }
#                 lines.append([0,0,vals])
#                 self.invoice_line_ids = lines



# car_ids = fields.One2many()

# result = []
# for line in used_car_ids:
#     result.append((0, 0, {'make': line.make, 'type': line.type}))
# self.car_ids = result

# (0, 0,  { values })    link to a new record that needs to be created with the given values dictionary
# (1, ID, { values })    update the linked record with id = ID (write *values* on it)
# (2, ID)                remove and delete the linked record with id = ID (calls unlink on ID, that will delete the object completely, and the link to it as well)

# Example:
# [(0, 0, {'field_name':field_value_record1, ...}), (0, 0, {'field_name':field_value_record2, ...})]



# @api.multi
#     def create_insurance_bill(self):
#         result = self.env['account.invoice'].create({
#             'partner_id': self.insurance_partner_id.id,
#             'shipment_id': self.id,
#             'name': 'Insurance Bill',
#             'type': 'in_invoice',
#             'origin': self.name,
#             'journal_id': self.insurance_journal_id.id,
#             'invoice_line_ids': [(0, 0, {
#                 'name': self.insurance_product_id.name,
#                 'origin': self.name,
#                 'account_id': self.insurance_product_id.property_account_expense_id.id,
#                 'price_unit': self.insurance_amount,
#                 'quantity': 1.0,
#                 'discount': 0.0,
#                 'uom_id': self.insurance_product_id.uom_id.id,
#                 'product_id': self.insurance_product_id.id,
#             })],
#         })

#  vals3 = {
#     'product_id': gaz[0].id,
#     'price_unit': gaz[0].list_price,
#     'name': gaz[0].name,
#     'uom_id': gaz[0].uom_id.id,
#     'quantity': 0,
#     'origin': "",
#     'company_id': gaz[0].company_id.id,
# }