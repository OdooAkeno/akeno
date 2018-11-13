# -*- coding: utf-8 -*-
from .tools import generer_ecritures


def ecritures_bulletin(r, journal, reference, name, bulletin, employee_partner,
                       montant):
    u"""Fonction utilisé pour générer les ecritures comptables de la paie."""
    journal_bulletin = bulletin.journal_id
    beneficiaire = employee_partner

    lignes_ecritures = {}
    lignes_ecritures['credit'] = []
    lignes_ecritures['debit'] = []

    lignes_ecritures['credit'].append({
        'compte': journal.default_credit_account_id.id,
        'montant': montant})

    lignes_ecritures['debit'].append({
        'compte': journal_bulletin.default_debit_account_id.id,
        'montant': montant})

    return generer_ecritures(r, journal, name, reference, None,
                             beneficiaire, lignes_ecritures)
