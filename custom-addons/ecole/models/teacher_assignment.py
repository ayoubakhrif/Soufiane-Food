from odoo import models, fields, api
from odoo.exceptions import ValidationError

class EcoleTeacherAssignment(models.Model):
    _name = 'ecole.teacher.assignment'
    _description = 'Affectation Professeur'

    teacher_id = fields.Many2one('ecole.teacher', string='Professeur', required=True, ondelete='cascade')
    class_id = fields.Many2one('ecole.class', string='Classe', required=True)
    subject_id = fields.Many2one('ecole.subject', string='Matière', required=True)
    available_subject_ids = fields.Many2many('ecole.subject', compute='_compute_available_subjects', store=False)

    _sql_constraints = [
        ('unique_teacher_class_subject', 
         'unique(teacher_id, class_id, subject_id)', 
         'Cette affectation existe déjà pour ce professeur !')
    ]

    @api.depends('class_id')
    def _compute_available_subjects(self):
        """Compute available subjects based on selected class"""
        for rec in self:
            if rec.class_id:
                rec.available_subject_ids = rec.class_id.subject_ids.mapped('subject_id')
            else:
                rec.available_subject_ids = False

    @api.onchange('class_id')
    def _onchange_class_id(self):
        """Reset subject when class changes"""
        if self.class_id:
            self.subject_id = False
            # Return domain to filter subjects by class
            class_subject_ids = self.class_id.subject_ids.mapped('subject_id')
            return {'domain': {'subject_id': [('id', 'in', class_subject_ids.ids)]}}
        else:
            self.subject_id = False
            return {'domain': {'subject_id': []}}

    @api.constrains('class_id', 'subject_id')
    def _check_subject_in_class(self):
        """Ensure the selected subject is assigned to the selected class"""
        for rec in self:
            if rec.class_id and rec.subject_id:
                class_subjects = rec.class_id.subject_ids.mapped('subject_id')
                if rec.subject_id not in class_subjects:
                    raise ValidationError(
                        f"La matière '{rec.subject_id.name}' n'est pas affectée à la classe '{rec.class_id.name}'."
                    )
