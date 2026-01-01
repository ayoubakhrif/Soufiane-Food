# -*- coding: utf-8 -*-
{
    'name': "Dashboards",
    'summary': """
        Centralized Management Dashboards for Executive Reporting.
    """,
    'description': """
        Provides read-only, aggregated dashboards for:
        - Kal3iya Inventory (Stock Value, Tonnage)
        - Kal3iya Performance (Sales, Margins)
    """,
    'author': "Ayoub Akhrif",
    'website': "http://www.yourcompany.com",
    'category': 'Reporting',
    'version': '0.1',
    'depends': ['base', 'kal3iya'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/dashboard_data.xml',
        'views/management_dashboard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
