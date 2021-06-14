from odoo import models, fields, api
import logging

class Breacker(models.Model):
    _name = 'breacker.breacker'
    
    menu = fields.Many2one('ir.ui.menu',sting="Menu",required=True)
    categ_id = fields.Many2one('ir.module.category',string="Categorie",required=True)
    
    @api.multi
    def separate(self,menu_id,categ_id):
        group = self.env['res.groups']
        if menu_id.child_id:
            result = group.create({
                'category_id':categ_id.id,
                'name':"Menu " + menu_id.complete_name
                })
            result.write({'users':[(4, self.env.user.id, 0)]})
            menu_id.write({'groups_id':[(4, result.id, 0)]})
            cat = categ_id
            for c in menu_id.child_id:
                self.separate(c,cat)
        else:
            result = group.create({
                'category_id':categ_id.id,
                'name':"Menu " + menu_id.complete_name
            })
            result.write({'users':[(4, self.env.user.id, 0)]})
            menu_id.write({'groups_id':[(4, result.id, 0)]})
                       
    @api.multi
    def compute_breacker(self):
        self.separate(self.menu,self.categ_id)
        
        
                
               
