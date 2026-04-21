{
    'name': 'Recap Balance',
    'version': '1.0',
    'category': 'Operations',
    'summary': 'Récapitulatif journalier du stock et de la trésorerie',
    'description': """
        Module de récapitulation journalière:
        - État du stock (Casa / Tanger)
        - Bénéfices du jour
        - Pertes du jour
        - Charges du jour
        - Crédits clients
        - Détails des transactions (Versements, Virements, Chèques)
    """,
    'author': 'Gestia',
    'depends': ['casa_stock', 'charges_casa'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/casa_recap_view.xml',
    ],
    'installable': True,
    'application': True,
}
