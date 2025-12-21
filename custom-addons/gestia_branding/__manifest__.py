{
    'name': 'Gestia Branding',
    'version': '17.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Replace Odoo branding with Gestia in browser title',
    'description': """
        This module replaces "Odoo" with "Gestia" in the browser tab title.
        No core file modifications - uses JavaScript override.
    """,
    'author': 'Ayoub Akhrif',
    'depends': ['web'],
    'data': [
        'views/web_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gestia_branding/static/src/webclient/title_service.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
