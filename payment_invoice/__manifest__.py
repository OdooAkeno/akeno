# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Payment Invoice',
    'version' : '1.0',
    'author':'Bayux',
    'category': 'Invoice',
    'maintainer': 'Bayux',
    'summary': """ Ajouter la facture dans la saisie des paiements.""",
    'description': """

        You can directly create invoice and set done to delivery order by single click

    """,
    'website': '',
    'license': 'LGPL-3',
    'support':'',
    'depends' : ['account'],
    'data': [
        'views/payment_invoice_views.xml',
    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,
}
