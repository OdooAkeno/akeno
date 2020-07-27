# -*- coding: utf-8 -*-
{
    'name': "Sale Return",

    'summary': """
        Sale Return Workflow""",

    'description': """
        Create a sale return seperately and create corresponding receipts
        and corresponding credit note.
    """,

    'author': "Bassam Infotech LLP",
    'website': "http://www.bassaminfotech.com",

    'category': 'Sale',
    'version': '12.0.0.1',

    'depends': ['base', 'sale', 'account'],
    'images': [
        'static/description/sale_return.png',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_return.xml',
        'data/ir_sequence_data.xml',
    ],
}
