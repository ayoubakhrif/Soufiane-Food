from odoo import models, fields, api

class Cal3iyaClient(models.Model):
    _name = 'finance.benif'
    _description = 'Bénificiaires'

    name = fields.Char(string='Bénificiaire', required=True)