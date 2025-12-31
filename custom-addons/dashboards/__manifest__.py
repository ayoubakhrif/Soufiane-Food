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
    'author': "Your Company",
    'website': "http://www.yourcompany.com",
    'category': 'Reporting',
    'version': '0.1',
    'depends': ['base', 'kal3iya'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/kal3iya_dashboard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
