from odoo import models, fields

class FinanceSte(models.Model):
    _name = 'finance.talon'
    _description = 'Talons'

    name = fields.Char(string='Talon', required=True)
    ste_id = fields.Many2one('finance.ste', string='Société', tracking=True, required=True)
