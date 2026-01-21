{
    'name': 'Réclamations',
    'version': '1.0',
    'summary': 'Manage internal claims',
    'description': """
        Réclamations Module
        ========================
        Track and follow up internal claims (e.g., DHL Delay).
    """,
    'category': 'Operations',
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'mail', 'web', 'logistique'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/claims_dhl_delay_view.xml',
        'views/claims_franchise_difference_view.xml',
        'views/supplier_view_ext.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
