from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SchoolGrade(models.Model):
    _name = 'school.grade'
    _description = 'Student Grade'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    student_id = fields.Many2one('school.student', string='Student', required=True, tracking=True)
    subject_id = fields.Many2one('school.subject', string='Subject', required=True, tracking=True)
    teacher_id = fields.Many2one('school.teacher', string='Evaluator', required=True, tracking=True)
    
    evaluation_type = fields.Selection([
        ('exam', 'Exam'),
        ('continuous', 'Continuous Assessment')
    ], string='Evaluation Type', default='continuous', required=True)
    
    score = fields.Float(string='Score (/20)', required=True, tracking=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    
    @api.constrains('score')
    def _check_score(self):
        for rec in self:
            if rec.score < 0 or rec.score > 20:
                raise ValidationError("Grade score must be between 0 and 20.")
                
    @api.onchange('subject_id')
    def _onchange_subject(self):
        if self.subject_id and self.subject_id.teacher_id:
            self.teacher_id = self.subject_id.teacher_id
