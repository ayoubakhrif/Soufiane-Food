{
    'name': 'Claims Management',
    'version': '1.0',
    'summary': 'Manage internal claims',
    'description': """
        Claims Management Module
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
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
