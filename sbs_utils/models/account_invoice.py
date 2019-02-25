# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

DATETIME_NOSEC = '%Y-%m-%d %H:%M'


def generer_facture(self, partner_id, origin_invoice, currency,
                    type_inv, lignes_factures, journal, extra_invoice):
    u"""Fonction pour générer une facture."""
    invoice_obj = self.env['account.invoice'].sudo()
    invoice_line_obj = self.env['account.invoice.line'].sudo()

    account = partner_id.property_account_receivable_id.id
    if type_inv == 'out_invoice':
        account = partner_id.property_account_payable_id.id

    v_invoice = {
        'partner_id': partner_id.id,
        'account_id': account,
        'type': type_inv,
        'date_invoice': (datetime.now() + timedelta(seconds=10)).strftime(
            DATETIME_NOSEC),
        'origin': origin_invoice,
        'currency_id': currency.id}

    if extra_invoice:
        v_invoice.update(extra_invoice)

    # on creait la nouvelle facture
    factureid = invoice_obj.create(v_invoice)

    # Create Invoice line
    line_common = {
        'invoice_id': factureid.id,
        'account_id': journal.default_debit_account_id.id}
    for elt in lignes_factures:
        elt.update(line_common)
        invoice_line_obj.create(elt)
