{
    'name': 'Generate Bons',
    'version': '1.0',
    'summary': 'Générer des factures proforma (bons) personnalisées',
    'author': 'Antigravity',
    'depends': ['base', 'company_data', 'custom_employee'],
    'data': [
        'security/ir.model.access.csv',
        'views/bon_article_views.xml',
        'views/bon_generation_views.xml',
        'views/menu_views.xml',
        'report/bon_report.xml',
        'report/bon_report_templates.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
