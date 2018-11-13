# -*- coding: utf-8 -*-
from odoo.exceptions import Warning, ValidationError
import re

######################################################################################
#  Source du code de conversion en chiffre                                           #
#    https://github.com/BADEP/addons/blob/8.0/amount_to_text_fr/amount_to_text_fr.py #
######################################################################################



correspondance = []

to_19_fr = (
    u'zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six',
    'sept', 'huit', 'neuf', 'dix', 'onze', 'douze', 'treize',
    'quatorze', 'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf')
tens_fr = (
    'vingt', 'trente', 'quarante', 'Cinquante', 'Soixante',
    'Soixante-dix', 'Quatre-vingts', 'Quatre-vingt Dix')
denom_fr = (
    '', 'Mille', 'Millions', 'Milliards', 'Billions', 'Quadrillions',
    'Quintillion', 'Sextillion', 'Septillion', 'Octillion', 'Nonillion',
    'Décillion', 'Undecillion', 'Duodecillion', 'Tredecillion',
    'Quattuordecillion', 'Sexdecillion', 'Septendecillion', 'Octodecillion',
    'Icosillion', 'Vigintillion')


# retourne les lignes d'ecritures
def get_lignes_ecritures(certif, liquidation, op):

    beneficiaire = certif.beneficiaire
    compte_depense = certif.compte_budgetaire.compte_prive
    compte_personnel = certif.compte_personnel

    taxes = liquidation.taxes if liquidation else None
    tva = liquidation.tva if liquidation else 0
    ir = liquidation.ir if liquidation else 0
    ttc = liquidation.ttc if liquidation else 0
    if liquidation:
        montant_liquidation = liquidation.montant_liquidation
    else:
        montant_liquidation = 0

    compte_beneficiare = beneficiaire.property_account_payable.id
    if compte_personnel:
        compte_beneficiare = compte_personnel.id

    lignes_ecritures = {}
    lignes_ecritures['credit'] = []
    lignes_ecritures['debit'] = []

    if not op:
        if not liquidation:
            lignes_ecritures['credit'].append({
                'compte': compte_beneficiare,
                'montant': certif.montant_depense})

            lignes_ecritures['debit'].append({
                'compte': compte_depense.id,
                'montant': certif.montant_depense})

        else:
            lignes_ecritures['credit'].append({
                'compte': compte_beneficiare,
                'montant': montant_liquidation})

            if tva > 0:
                la_tva = taxes.filtered(lambda r: 'tva' in r.name.lower())
                if la_tva:
                    compte_tva = la_tva[0].account_collected_id
                    lignes_ecritures['credit'].append({
                        'compte': compte_tva.id,
                        'montant': tva})

            if ir > 0:
                lir = taxes.filtered(lambda r: 'ir' in r.name.lower())
                if lir:
                    compte_ir = lir[0].account_collected_id
                    lignes_ecritures['credit'].append({
                        'compte': compte_ir.id,
                        'montant': ir})

            lignes_ecritures['debit'].append({
                'compte': compte_depense.id,
                'montant': ttc})
    else:
        journal_bank = op.compte_debiter.journal_id
        compte_tresorerie = journal_bank.default_credit_account_id
        montant_op = op.montant_op

        if not op.op_taxe:
            lignes_ecritures['debit'].append({
                'compte': compte_beneficiare,
                'montant': montant_op})
        else:
            if tva > 0:
                latva = taxes.filtered(lambda x: 'tva' in x.name.lower())
                if latva:
                    compte_tva = latva[0].account_collected_id
                    lignes_ecritures['debit'].append({
                        'compte': compte_tva.id,
                        'montant': tva})

            if ir > 0:
                lir = taxes.filtered(lambda x: 'ir' in x.name.lower())
                if lir:
                    compte_ir = lir[0].account_collected_id
                    lignes_ecritures['debit'].append({
                        'compte': compte_ir.id,
                        'montant': ir})

        lignes_ecritures['credit'].append({
            'compte': compte_tresorerie.id,
            'montant': montant_op})

    return lignes_ecritures


# genere les ecritures comptables
def generer_ecritures(self, journal, reference, name, unite_gestion,
                      beneficiaire, lignes_ecritures):

    account_move_obj = self.env['account.move']
    account_move_line_obj = self.env['account.move.line'].with_context(
        check_move_validity=False)
    piece_comptable = None

    if not journal:
        raise ValidationError('Pas de journal pour cette ecriture comptable')

    # creation de la piece comptable
    vals = {}
    vals['journal_id'] = journal.id
    vals['ref'] = reference
    piece_comptable = account_move_obj.with_context(
        apply_taxes=True).create(vals)

    vals = {}
    vals['name'] = name
    vals['move_id'] = piece_comptable.id
    vals['ref'] = reference
    vals['analytic_id'] = unite_gestion.id if unite_gestion else None
    vals['partner_id'] = beneficiaire.id if beneficiaire else None

    credit = lignes_ecritures['credit']
    for ligne in credit:
        # ecriture de credit
        vals['account_id'] = ligne['compte']
        vals['credit'] = ligne['montant']
        vals['debit'] = 0
        account_move_line_obj.create(vals)

    debit = lignes_ecritures['debit']
    for ligne in debit:
        # ecriture de debit
        vals['account_id'] = ligne['compte']
        vals['debit'] = ligne['montant']
        vals['credit'] = 0
        account_move_line_obj.create(vals)

    return piece_comptable.id


def format_amount_to_integer(amount):
    """
    Convertit un nombre decimal en un entier.

    fonction qui formate un entier et le convertit en entier
    l'entier utilise est celui le plus proche du nombre decimal.
    """
    amount = int(round(amount))
    return '{0:,}'.format(amount).replace(',', ' ')


def amount_to_text_fr_corrected(valeur, devise):
    res = amount_to_text_fr(valeur, devise)

    # enleve le zero cent
    # res = res.replace('zéro Cent', '').strip()
    rep = res

    for elt in correspondance:
        r_comp = re.compile(elt[0])
        rep = r_comp.sub(elt[1], rep)
    return rep[:-14]


def _convert_nn_fr(val):
    """ convert a value < 100 to French
    """
    if val < 20:
        return to_19_fr[val]
    for (dcap, dval) in ((k, 20 + (10 * v)) for (v, k) in enumerate(tens_fr)):
        if dval + 10 > val:
            if val % 10:
                if dval == 70 or dval == 90:
                    return tens_fr[dval / 10 - 3] + '-' + to_19_fr[val % 10 + 10]
                else:
                    return dcap + '-' + to_19_fr[val % 10]
            return dcap


def _convert_nnn_fr(val):
    """ convert a value < 1000 to french

        special cased because it is the level that kicks
        off the < 100 special case.  The rest are more general.
        This also allows you to
        get strings in the form of 'forty-five hundred' if called directly.
    """
    word = ''
    (mod, rem) = (val % 100, val // 100)
    if rem > 0:
        if rem == 1:
            word = 'Cent'
        else:
            word = to_19_fr[rem] + ' Cent'
        if mod > 0:
            word += ' '
    if mod > 0:
        word += _convert_nn_fr(mod)
    return word


def french_number(val):
    if val < 100:
        return _convert_nn_fr(val)
    if val < 1000:
        return _convert_nnn_fr(val)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom_fr))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            if l == 1:
                ret = denom_fr[didx]
            else:
                ret = _convert_nnn_fr(l) + ' ' + denom_fr[didx]
            if r > 0:
                ret = ret + ', ' + french_number(r)
            return ret


def amount_to_text_fr(number, currency):
    number = '%.2f' % number
    units_name = currency
    list = str(number).split('.')
    start_word = french_number(abs(int(list[0])))
    end_word = french_number(int(list[1]))
    cents_number = int(list[1])
    cents_name = (cents_number > 1) and ' Centimes' or ' Centime'
    final_result = start_word + ' ' + units_name
    final_result += ' ' + end_word + ' ' + cents_name
    return final_result
