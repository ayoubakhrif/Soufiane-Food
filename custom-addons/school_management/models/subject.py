from odoo import models, fields, api

class SchoolSubject(models.Model):
    _name = 'school.subject'
    _description = 'School Subject'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Subject Name', required=True, tracking=True)
    coefficient = fields.Float(string='Coefficient', default=1.0, required=True, tracking=True)
    class_id = fields.Many2one('school.class', string='Class', required=True, tracking=True)
    teacher_id = fields.Many2one('school.teacher', string='Teacher', help="Teacher responsible for this subject in this class")
