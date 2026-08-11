from odoo import models, fields

class Finance2Personne(models.Model):
    _name = 'finance2.personne'
    _description = 'Personne (Logistique)'

    name = fields.Char(string='Nom complet', required=True)
    active = fields.Boolean(default=True)

class Finance2Ste(models.Model):
    _name = 'finance2.ste'
    _description = 'Société'

    name = fields.Char(string='Nom de la société', required=True)
    active = fields.Boolean(default=True)

class Finance2Benif(models.Model):
    _name = 'finance2.benif'
    _description = 'Bénéficiaire'

    name = fields.Char(string='Nom du bénéficiaire', required=True)
    active = fields.Boolean(default=True)
