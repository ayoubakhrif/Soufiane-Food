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
    'category': 'Reporting',
    'version': '0.1',
    'depends': ['base', 'kal3iya', 'logistique', 'claims'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/dashboard_data.xml',
        'data/surest_dashboard_data.xml',
        'views/surest_mag_dashboard_views.xml',
        'views/management_dashboard_views.xml',
        'views/surest_mag_report_view.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
