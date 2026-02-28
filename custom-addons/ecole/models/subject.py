from odoo import models, fields

class EcoleSubject(models.Model):
    _name = 'ecole.subject'
    _description = 'Matière'

    name = fields.Char(string='Nom', required=True)
    code = fields.Char(string='Code')
