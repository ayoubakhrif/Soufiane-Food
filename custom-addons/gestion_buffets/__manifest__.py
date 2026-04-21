# -*- coding: utf-8 -*-
{
    'name': 'Gestion Buffets',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Gestion des buffets, packs, lieux et charges',
    'description': """
        Module pour gérer les événements de type buffet.
    """,
    'author': 'Soufiane-Food',
    'depends': ['base', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/buffet_master_data_views.xml',
        'views/gestion_buffet_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
