from odoo import models, fields, api

class SchoolClass(models.Model):
    _name = 'school.class'
    _description = 'School Class'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Class Name', required=True, tracking=True, help="e.g. Grade 5 A")
    level = fields.Selection([
        ('primary', 'Primary'),
        ('middle', 'Middle School'),
        ('high', 'High School')
    ], string='Education Level', required=True)
    
    academic_year = fields.Char(string='Academic Year', required=True, tracking=True)
    
    teacher_id = fields.Many2one('school.teacher', string='Home Room Teacher', tracking=True)
    
    student_ids = fields.One2many('school.student', 'current_class_id', string='Students')
    subject_ids = fields.One2many('school.subject', 'class_id', string='Subjects')
