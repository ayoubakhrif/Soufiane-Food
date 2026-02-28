from odoo import models, fields, api

class EcoleClassSubject(models.Model):
    _name = 'ecole.class.subject'
    _description = 'Matière par Classe'

    class_id = fields.Many2one('ecole.class', string='Classe', required=True, ondelete='cascade')
    subject_id = fields.Many2one('ecole.subject', string='Matière', required=True)
    coefficient = fields.Float(string='Coefficient', default=1.0)

    _sql_constraints = [
        ('unique_class_subject', 'unique(class_id, subject_id)', 'La matière doit être unique par classe !')
    ]
