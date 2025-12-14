from odoo import models, fields, api

class EcoleClass(models.Model):
    _name = 'ecole.class'
    _description = 'Classe'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom de la classe', required=True, tracking=True)
    level = fields.Selection([
        ('primary', 'Primaire'),
        ('middle', 'Collège'),
        ('high', 'Lycée')
    ], string='Niveau', required=True)
