{
    'name': 'Suivi Personnel',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Personal Income and Expense Tracking',
    'description': """
Suivi Personnel
===============
Simple and independent module for personal finance management.

Features:
- Track daily and monthly incomes
- Track daily and monthly expenses
- Configurable accounting month start day
- Analysis with pivot and graph views
- No workflow, direct data entry
    """,
    'author': 'Ayoub Akhrif',
    'depends': ['base', 'web'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/suivi_config_views.xml',
        'views/month_report_views.xml',
        'views/expense_category_views.xml',
        'views/income_monthly_views.xml',
        'views/income_daily_views.xml',
        'views/expense_monthly_views.xml',
        'views/expense_daily_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
