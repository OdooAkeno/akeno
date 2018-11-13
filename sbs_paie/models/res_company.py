# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):

    _inherit = "res.company"

    nbr_annee_avanc = fields.Integer(
        string='Nombres d\'années avant avancement',
        required=True,
        default=2,
        help="Valeur du nombre d'annnée avant un nouvel avancement")

    numero_employeur = fields.Char(
        'Numero employeur',
        size=10)

    cle_numero_employeur = fields.Char(
        string='Cle umero employeur',
        size=1)

    regime_employeur = fields.Integer('Regime employeur')

    numero_contribuable = fields.Char(
        'Numero Contribuable',
        size=14)

    code_enregistrement = fields.Char('Code enregistrement')

    numero_dipe = fields.Char(
        'Numero DIPE',
        size=5)

    cle_numero_dipe = fields.Char(
        'Cle Numero DIPE',
        size=1)

    @api.constrains('regime_employeur')
    def _check_regime_employeur(self):
        for r in self:
            valeur = str(r.regime_employeur)
            if len(valeur) > 1:
                raise ValidationError(
                    '1 caractere max pour le champ regime employeur')

    @api.constrains('code_enregistrement')
    def _check_code_enregistrement(self):
        for r in self:
            valeur = str(r.code_enregistrement)
            if len(valeur) > 3:
                raise ValidationError(
                    '3 caracteres max pour le champ code enregistrement')
