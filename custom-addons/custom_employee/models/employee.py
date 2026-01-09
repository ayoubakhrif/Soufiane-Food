from odoo import models, fields, api, exceptions

class CoreEmployee(models.Model):
    _name = 'core.employee'
    _description = 'Employee'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'avatar.mixin']
    _rec_name = 'name'

    # Personal Information
    name = fields.Char(string='Full Name', required=True, tracking=True)
    cin = fields.Char(string='CIN (Carte national)', tracking=True)
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    rib = fields.Char(string='RIB (Bank Account)', tracking=True)
    monthly_salary = fields.Float(string='Salaire banque', tracking=True)
    cnss_salary = fields.Float(string='Salaire CNSS', tracking=True)
    declared_days = fields.Integer(string='Jours déclarés', tracking=True)
    signature = fields.Binary(string='Signature')

    # Organizational Information
    job_title = fields.Char(string='Job Position', tracking=True)
    department = fields.Char(string='Department', tracking=True)
    site = fields.Char(string='Site')
    entry_date = fields.Date(string='Date entrée', tracking=True)
    contract_date = fields.Date(string='Date de contrat', tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    matriculation_cnss = fields.Char(string='Matriculation CNSS', tracking=True)
    matriculation = fields.Char(string='Matriculation', tracking=True)

    # Hierarchy
    parent_id = fields.Many2one('core.employee', string='Manager', index=True, tracking=True)
    child_ids = fields.One2many('core.employee', 'parent_id', string='Direct Subordinates')

    # System Access
    user_id = fields.Many2one('res.users', string='Related User', help='Link this employee to a system user for login access.')

    @api.constrains('parent_id')
    def _check_parent_id(self):
        for employee in self:
            if not employee.parent_id:
                continue
            
            # Check for self-reference
            if employee.parent_id == employee:
                raise exceptions.ValidationError("Un employée ne peut pas etre le manager de lui meme!")
            
            # Check for circular dependency
            level = 100
            current = employee
            while current.parent_id and level > 0:
                current = current.parent_id
                if current == employee:
                    raise exceptions.ValidationError("You cannot create a circular hierarchy loop!")
                level -= 1
