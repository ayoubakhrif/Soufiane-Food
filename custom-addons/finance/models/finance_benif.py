from odoo import models, fields, api

class Cal3iyaClient(models.Model):
    _name = 'finance.benif'
    _description = 'Bénificiaires'

    name = fields.Char(string='Bénificiaire', required=True)
    days = fields.Integer(string='Jours de plus')
    type = fields.Selection([
        ('import', 'Importation'),
        ('divers', 'Divers'),
        ], string='Imp/Div', required=True, store=True)