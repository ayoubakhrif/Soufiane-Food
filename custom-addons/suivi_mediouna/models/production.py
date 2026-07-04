from odoo import models, fields

class Production(models.Model):
    _name = 'suivi_mediouna.production'
    _description = 'Gestion de Production'
    _order = 'date desc'

    date = fields.Date(string='Jour', required=True, default=fields.Date.context_today)
    ville = fields.Selection([
        ('mediouna', 'Mediouna'),
        ('agadir', 'Agadir')
    ], string='Ville', required=True, default='mediouna')
    produit = fields.Char(string='Produit', required=True)
    quantite = fields.Float(string='Quantité', required=True)
    montant = fields.Float(string='Montant', required=True)
