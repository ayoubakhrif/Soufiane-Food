from odoo import models, fields, api
from datetime import date

class SchoolStudent(models.Model):
    _name = 'school.student'
    _description = 'School Student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'registration_number'

    registration_number = fields.Char(string='Registration Number', required=True, copy=False, readonly=True, default='New')
    first_name = fields.Char(string='First Name', required=True, tracking=True)
    last_name = fields.Char(string='Last Name', required=True, tracking=True)
    date_of_birth = fields.Date(string='Date of Birth', tracking=True)
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender', tracking=True)
    
    photo = fields.Binary(string='Photo', attachment=True)
    
    parent_id = fields.Many2one('school.parent', string='Parent/Guardian', required=True, tracking=True)
    grade_ids = fields.One2many('school.grade', 'student_id', string='Grades')
    
    current_class_id = fields.Many2one('school.class', string='Current Class', tracking=True)
    academic_year = fields.Char(string='Academic Year', tracking=True, help="e.g. 2023-2024")
    
    status = fields.Selection([
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('withdrawn', 'Withdrawn')
    ], string='Status', default='active', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('registration_number', 'New') == 'New':
            vals['registration_number'] = self.env['ir.sequence'].next_by_code('school.student') or 'New'
        return super(SchoolStudent, self).create(vals)

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.date_of_birth:
                rec.age = today.year - rec.date_of_birth.year - ((today.month, today.day) < (rec.date_of_birth.month, rec.date_of_birth.day))
            else:
                rec.age = 0
            
    def name_get(self):
        result = []
        for rec in self:
            name = f"[{rec.registration_number}] {rec.first_name} {rec.last_name}"
            result.append((rec.id, name))
        return result
