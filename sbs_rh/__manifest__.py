{
    'name': "Ressources humaines",
    'version': '1.0',
    'author': "SBS",
    'category': 'Human Resources',
    'description': """
        Module de gestion des ressources humaines.
    """,
    'depends': [
        'base',
        'sbs_utils',
        'hr',
        'hr_contract',
        # 'purchase',
        # 'portal_sale',
        # 'web',
        # 'hr_expense'
    ],
    # data files always loaded at installation
    'data': [
        # sequences
        # "data/sequences.xml",

        # reports
        # "reports/brouillard_caisse_report.xml",
        # "reports/autorisation_decais_report.xml",
        # "reports/bon_encais_report.xml",

        # menus
        "views/menu.xml",

        # views
        "views/hr_employee_views.xml",
        "views/hr_contract_views.xml",
        # "views/categorie_salariale_views.xml",

        # security
        # "security/security.xml",
        # "security/security_menu.xml",
        # "security/ir.model.access.csv",

        # wizards
        # "wizards/brouillard_caisse_wizard.xml",

    ],
    'css': ['static/src/css/my_css.css'],

    # data files containing optionally loaded demonstration data
    'demo': [],
    "license": 'LGPL-3',
    'installable': True
}
