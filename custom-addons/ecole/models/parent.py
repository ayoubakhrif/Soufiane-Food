from odoo import models, fields, api
from odoo.exceptions import ValidationError

class EcoleParent(models.Model):
    _name = 'ecole.parent'
    _description = 'Parent'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom complet', required=True, tracking=True)
    phone = fields.Char(string='Téléphone', tracking=True)
    address = fields.Text(string='Adresse', tracking=True)
    student_ids = fields.One2many('ecole.student', 'parent_id', string='Enfants')

    @api.constrains('phone')
    def _check_phone(self):
        for rec in self:
            if rec.phone and not rec.phone.isdigit():
                raise ValidationError("Le numéro de téléphone ne doit contenir que des chiffres.")