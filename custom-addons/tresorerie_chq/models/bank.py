from odoo import models, fields

class TresorerieChqBank(models.Model):
    _name = 'tresorerie_chq.bank'
    _description = 'Banque'
    _order = 'name'

    name = fields.Char(string='Nom de la Banque', required=True)
    active = fields.Boolean(string='Actif', default=True)
