# -*- coding: utf-8 -*-
from odoo import models, fields


# cette classe permet de configurer les echellons
class EchelonSalariale(models.Model):

    _name = "aft_paie.echelon_salariale"

    name = fields.Char(string="Libelle", required=True)

    code = fields.Char(string="Code", required=True)

    num_ordre = fields.Integer(string="Numéro d'ordre", required=True)
