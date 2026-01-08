{
    'name': 'Transport Management',
    'version': '1.0',
    'summary': 'Manage transport trips and charges',
    'description': """
        Transport Management Module
        ===========================
        Track transport trips and analyze charges by driver, client, and types.
    """,
    'category': 'Logistics',
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'hr', 'contacts', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/transport_trip_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
