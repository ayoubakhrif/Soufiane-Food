{
    'name': 'Database Backup to Google Drive',
    'version': '17.0.1.0.0',
    'category': 'Utilities',
    'summary': 'Automated database backups to a specific Google Drive folder.',
    'author': 'Antigravity',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/backup_config_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
