# -*- coding: utf-8 -*-


def create_payment(payment_obj, montant, name, currency_id, journal_id,
                   partner_id, partner_type, date, payment_method_id,
                   payment_method_type, facture_id=None, transaction_id=False,
                   destination_journal_id=None):

    values = {
        "amount": montant or 0.0,
        "communication": name,
        "currency_id": currency_id,
        "destination_journal_id": destination_journal_id,
        "journal_id": journal_id,
        "partner_id": partner_id,
        "partner_type": partner_type,
        "payment_date": date,
        "payment_method_id": payment_method_id,
        "payment_transaction_id": transaction_id,
        "payment_type": payment_method_type}

    if facture_id:
        values['invoice_ids'] = [(4, facture_id, None)]

    res = payment_obj.create(values)
    res.post()
    return res
