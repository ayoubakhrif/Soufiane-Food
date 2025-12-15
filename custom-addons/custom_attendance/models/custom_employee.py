from odoo import models, fields

class CustomEmployee(models.Model):
    _name = 'custom.employee'
    _description = 'Custom Employee'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Full Name', required=True, tracking=True)
    phone = fields.Char(string='Phone Number', tracking=True)
    monthly_salary = fields.Float(string='Monthly Salary', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    
    attendance_ids = fields.One2many('custom.attendance', 'employee_id', string='Attendances')
