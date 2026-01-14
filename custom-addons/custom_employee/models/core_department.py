from odoo import models, fields, api, exceptions

class CoreDepartment(models.Model):
    _name = 'core.department'
    _description = 'Department'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char(string='Department Name', required=True, tracking=True, index=True)
    code = fields.Char(string='Code', tracking=True, index=True)
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        recursive=True,
        store=True
    )
    
    parent_id = fields.Many2one(
        'core.department',
        string='Parent Department',
        ondelete='restrict',
        index=True,
        tracking=True
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('core.department', 'parent_id', string='Child Departments')
    
    manager_id = fields.Many2one(
        'core.employee',
        string='Manager',
        tracking=True,
        help='Department manager/head'
    )
    
    active = fields.Boolean(string='Active', default=True, tracking=True)
    color = fields.Integer(string='Color Index', default=0)
    
    # Statistics
    employee_count = fields.Integer(
        string='Employee Count',
        compute='_compute_employee_count'
    )
    
    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Department code must be unique!'),
    ]

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for department in self:
            if department.parent_id:
                department.complete_name = f"{department.parent_id.complete_name} / {department.name}"
            else:
                department.complete_name = department.name

    def _compute_employee_count(self):
        employee_data = self.env['core.employee']._read_group(
            [('department_id', 'in', self.ids)],
            ['department_id'],
            ['__count']
        )
        result = {department.id: count for department, count in employee_data}
        for department in self:
            department.employee_count = result.get(department.id, 0)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise exceptions.ValidationError('You cannot create recursive departments!')

    def name_get(self):
        result = []
        for department in self:
            result.append((department.id, department.complete_name))
        return result
