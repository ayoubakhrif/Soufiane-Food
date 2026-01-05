from odoo import models, fields, api

class Cal3iyaClient(models.Model):
    _name = 'finance.benif'
    _description = 'Bénificiaires'

    name = fields.Char(string='Bénificiaire', required=True)
    days = fields.Integer(string='Jours de plus')
    type = fields.Selection([
        ('import', 'Importation'),
        ('divers', 'Divers'),
        ('bureau', 'Bureau'),
        ('annule', 'Annulé'),
        ], string='Imp/Div', required=True, store=True)

    benif_deduction = fields.Boolean(string="Autorise Paiement par Déduction", default=False)