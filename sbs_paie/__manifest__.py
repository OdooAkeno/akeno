{
    'name': "Gestion de la paie",
    'version': '1.0',
    'author': "SBS",
    'category': 'Human Resources',
    'description': """
        Module de gestion de la paie.
    """,
    'depends': [
        'base',
        'sbs_utils',
        'payroll_timesheet',
        'sbs_rh',
        # 'purchase',
        # 'portal_sale',
        # 'web',
        # 'hr_expense'
    ],
    # data files always loaded at installation
    'data': [
        # sequences
        "data/sequences.xml",
        "data/mail_subtypes.xml",

        # reports
        "reports/papers.xml",
        "reports/elements_gains_report.xml",
        "reports/elements_retenues_report.xml",
        "reports/elements_patronal_report.xml",
        "reports/dipes_report.xml",
        "reports/bulletin_paie_report.xml",

        # menus
        "views/menu.xml",

        # views
        "views/hr_contract_type_views.xml",
        "views/hr_contract_views.xml",
        "views/categorie_salariale_views.xml",
        "views/echelon_salariale_views.xml",
        "views/grille_salaire_views.xml",
        "views/prime_ret_views.xml",
        "views/hr_payslip_views.xml",
        "views/avancement_views.xml",
        "views/res_company_views.xml",
        "views/hr_payslip_run_views.xml",
        "views/categorie_bulletin_views.xml",

        # security
        # "security/security.xml",
        # "security/security_menu.xml",
        "security/ir.model.access.csv",

        # wizards
        "wizards/view_elements_gains_wiz.xml",
        "wizards/view_elements_retenues_wiz.xml",
        "wizards/view_elements_patronal_wiz.xml",
        "wizards/view_dipes_wiz.xml",

        # data to import
        "data/data.xml",
        "data/cron.xml",

    ],
    'css': ['static/src/css/my_css.css'],

    # data files containing optionally loaded demonstration data
    'demo': [],
    "license": 'LGPL-3',
    'installable': True
}
