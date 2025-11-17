# gestia_branding/__manifest__.py
{
    "name": "Gestia Branding",
    "summary": "Remplacement complet du branding Odoo par Gestia",
    "version": "16.0.1.0.0",
    "category": "Web",
    "author": "Gestia",
    "website": "https://gestia.ma",
    "license": "LGPL-3",
    "depends": ["web"],
    "data": [
        "views/gestia_webclient.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # ici si tu veux ajouter du CSS plus tard
        ],
        "web.assets_frontend": [
            # idem pour le site / login
        ],
    },
    "installable": True,
    "application": False,
}
