from odoo import models, fields

class FinancePerso(models.Model):
    _name = 'finance.perso'
    _description = 'Personnes'

    name = fields.Char(string='Personnes', required=True)
    contact_id = fields.Many2one('contacts.casa', string='Contact SF')
