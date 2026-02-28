from odoo import models, fields, api

class SchoolAcademicReport(models.Model):
    _name = 'school.academic.report'
    _description = 'Academic Report Card'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    student_id = fields.Many2one('school.student', string='Student', required=True)
    class_id = fields.Many2one('school.class', string='Class', related='student_id.current_class_id', store=True)
    academic_year = fields.Char(string='Academic Year', related='student_id.academic_year', store=True)
    
    report_date = fields.Date(string='Report Date', default=fields.Date.context_today)
    
    average = fields.Float(string='Overall Average', compute='_compute_average', store=True)
    mention = fields.Selection([
        ('excellent', 'Excellent'),
        ('very_good', 'Very Good'),
        ('good', 'Good'),
        ('satisfactory', 'Satisfactory'),
        ('needs_improvement', 'Needs Improvement')
    ], string='Mention', compute='_compute_mention', store=True)
    
    @api.depends('student_id', 'class_id')
    def _compute_average(self):
        for rec in self:
            grades = self.env['school.grade'].search([
                ('student_id', '=', rec.student_id.id),
                # Considering all grades for the student, ideally this should filter by academic year/period
                # But for simplicity in this scope, we take all grades linked to the student.
                # In a real scenario, we would filter by date range of the academic year.
            ])
            
            total_weighted_score = 0
            total_coefficient = 0
            
            # Helper to average grades per subject first? 
            # Usual logic: Average of Subject = (Exam + Continuous)/2 or similar.
            # Simplified Logic: Weighted average of all individual grades based on subject coefficient.
            
            for grade in grades:
                coef = grade.subject_id.coefficient or 1.0
                total_weighted_score += grade.score * coef
                total_coefficient += coef
                
            if total_coefficient > 0:
                rec.average = total_weighted_score / total_coefficient
            else:
                rec.average = 0.0

    @api.depends('average')
    def _compute_mention(self):
        for rec in self:
            avg = rec.average
            if avg >= 18:
                rec.mention = 'excellent'
            elif avg >= 16:
                rec.mention = 'very_good'
            elif avg >= 14:
                rec.mention = 'good'
            elif avg >= 12:
                rec.mention = 'satisfactory'
            else:
                rec.mention = 'needs_improvement'
