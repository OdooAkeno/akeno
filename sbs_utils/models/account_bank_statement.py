# -*- coding: utf-8 -*-


def create_session(bankstat_obj, journal_id, date):
    u"""Crée une nouvelle session."""
    values = {'journal_id': journal_id, 'date': date}
    session = bankstat_obj.create(values)

    last_bnk_stmt = bankstat_obj.search([
        ('journal_id', '=', journal_id),
        ('date_done', '!=', False)], limit=1)
    opening = last_bnk_stmt.balance_end if last_bnk_stmt else 0.0
    session.balance_start = opening
    return session


def get_current_session(bankstat_obj, journal_id,
                        do_create_session=False, date=None):
    """Retourne la session en cours d'un journal de caisse."""
    res = bankstat_obj.search([
        ('state', '=', "open"),
        ('journal_id', '=', journal_id)],
        limit=1)
    if not res and do_create_session and date:
        res = create_session(bankstat_obj, journal_id, date)

    return res
