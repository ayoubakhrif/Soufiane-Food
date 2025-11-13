from odoo import models, fields

class Cal3iyaprovider(models.Model):
    _name = 'cal3iya.provider'
    _description = 'Fournisseurs'

    name = fields.Char(string='Fournisseur', required=True)