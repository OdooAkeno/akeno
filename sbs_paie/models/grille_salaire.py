# -*- coding: utf-8 -*-
from odoo import api, fields, models


class GrilleSalaire(models.Model):

    _inherit = ['mail.thread']
    _name = 'aft_paie.grille_salaire'
    _description = 'Grille salariale'
    _rec_name = "code"
    _order = "num_ordre asc"

    name = fields.Char(string="Description", required=True)

    types_contrat = fields.Many2many(
        string='Type de contrat de cette grille',
        required=True,
        help="type de contrat prenant en charge cette grille",
        comodel_name='hr.contract.type',
        relation='model_grille_to_typecontrat')

    code = fields.Char(string="Code", required=True)

    montant = fields.Float(
        string="Salaire",
        required=True,
        digits=(16, 2))

    num_ordre = fields.Integer(
        string="Numero d'ordre",
        required=True)

    categ_id = fields.Many2one(
        comodel_name='aft_paie.categorie_salariale',
        string="Categorie salariale")

    ech_id = fields.Many2one(
        comodel_name='aft_paie.echelon_salariale',
        string="Echellon")

    @api.onchange('categ_id', 'ech_id')
    def onchange_num_ordre(self):
        if self.categ_id and self.ech_id:
            self.code = str(self.categ_id.code + self.ech_id.code).upper()
            self.num_ordre = self.categ_id.num_ordre * 10
            self.num_ordre += self.ech_id.num_ordre
