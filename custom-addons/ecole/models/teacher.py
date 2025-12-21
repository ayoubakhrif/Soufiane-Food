from odoo import models, fields

class EcoleTeacher(models.Model):
    _name = 'ecole.teacher'
    _description = 'Professeur'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    first_name = fields.Char(string='Prénom', required=True, tracking=True)
    last_name = fields.Char(string='Nom', required=True, tracking=True)
    phone = fields.Char(string='Numéro de téléphone', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    rib = fields.Char(string='RIB', tracking=True)
    assignment_ids = fields.One2many('ecole.teacher.assignment', 'teacher_id', string='Affectations')

    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.first_name} {rec.last_name}"
            result.append((rec.id, name))
        return result
