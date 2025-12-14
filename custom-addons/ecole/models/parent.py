from odoo import models, fields, api

class EcoleParent(models.Model):
    _name = 'ecole.parent'
    _description = 'Parent'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom complet', required=True, tracking=True)
    phone = fields.Char(string='Téléphone', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    address = fields.Text(string='Adresse')
    student_ids = fields.One2many('ecole.student', 'parent_id', string='Enfants')