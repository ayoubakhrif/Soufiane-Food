from odoo import models, fields, api

class SchoolTeacher(models.Model):
    _name = 'school.teacher'
    _description = 'School Teacher'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Teacher Name', required=True, tracking=True)
    phone = fields.Char(string='Phone Number')
    email = fields.Char(string='Email Address')
    
    subject_ids = fields.Many2many('school.subject', string='Subjects Type Taught') 
    # Note: If subjects are strictly linked to classes, this M2M might need to be 'subjects I am responsible for'. 
    # For now, I will interpret this as "types of subjects" or specific class-subjects. 
    # Given the requirements: "Subjects... class to which the subject belongs", a subject is "Math - Class 5A".
    # So a teacher can teach multiple of these.

    active = fields.Boolean(default=True)
