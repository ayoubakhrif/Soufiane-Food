from odoo import models, fields, api

class SchoolParent(models.Model):
    _name = 'school.parent'
    _description = 'School Parent'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Full Name', required=True, tracking=True)
    phone = fields.Char(string='Phone Number', tracking=True)
    email = fields.Char(string='Email Address', tracking=True)
    address = fields.Text(string='Physical Address')
    
    student_ids = fields.One2many('school.student', 'parent_id', string='Children')

    _sql_constraints = [
        ('unique_email', 'unique(email)', 'Email address must be unique for each parent.')
    ]
