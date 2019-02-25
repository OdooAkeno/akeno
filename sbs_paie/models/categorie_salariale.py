# -*- coding: utf-8 -*-
from odoo import models, fields


class CategorieSalariale(models.Model):

    _name = "sbs_paie.categorie_salariale"
    _description = u"Catégorie de salaire"

    name = fields.Char(string="Libelle", required=True)

    code = fields.Char(string="Code", required=True)

    num_ordre = fields.Integer(string="Numéro d'ordre", required=True)
