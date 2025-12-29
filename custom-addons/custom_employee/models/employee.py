from odoo import models, fields, api, exceptions

class CustomEmployee(models.Model):
    _name = 'custom.employee'
    _description = 'Employee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # Personal Information
    name = fields.Char(string='Full Name', required=True, tracking=True)
    image_1920 = fields.Image(string='Photo', max_width=1920, max_height=1920)
    cin = fields.Char(string='CIN (National ID)', tracking=True)
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    rib = fields.Char(string='RIB (Bank Account)')
    signature = fields.Binary(string='Signature')

    # Organizational Information
    job_title = fields.Char(string='Job Position', tracking=True)
    department = fields.Char(string='Department', tracking=True)
    site = fields.Char(string='Site / Location')
    entry_date = fields.Date(string='Entry Date', default=fields.Date.context_today)
    active = fields.Boolean(string='Active', default=True, tracking=True)

    # Hierarchy
    parent_id = fields.Many2one('custom.employee', string='Manager', index=True, tracking=True)
    child_ids = fields.One2many('custom.employee', 'parent_id', string='Direct Subordinates')

    # System Access
    user_id = fields.Many2one('res.users', string='Related User', help='Link this employee to a system user for login access.')

    @api.constrains('parent_id')
    def _check_parent_id(self):
        for employee in self:
            if not employee.parent_id:
                continue
            
            # Check for self-reference
            if employee.parent_id == employee:
                raise exceptions.ValidationError("An employee cannot be their own manager!")
            
            # Check for circular dependency
            level = 100
            current = employee
            while current.parent_id and level > 0:
                current = current.parent_id
                if current == employee:
                    raise exceptions.ValidationError("You cannot create a circular hierarchy loop!")
                level -= 1
