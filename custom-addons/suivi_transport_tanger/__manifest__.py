# -*- coding: utf-8 -*-
{
    'name': 'Suivi Transport',
    'version': '1.0',
    'category': 'Transport',
    'summary': 'Suivi des opérations de transport par chauffeur.',
    'description': """
        Ce module gère le suivi des opérations de transport.
        - Gestion des Chauffeurs
        - Gestion des Clients
        - Suivi des opérations avec détail (Client, Article)
    """,
    'author': 'Soufiane Food',
    'website': '',
    'depends': ['base', 'company_data', 'custom_employee', 'casa_stock', 'stock_kal3iya'],
    'data': [
        'data/sequence.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/suivi_operation_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
