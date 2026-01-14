from odoo import models, fields, api, exceptions

class CoreJobPosition(models.Model):
    _name = 'core.job.position'
    _description = 'Job Position'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'name'
    _order = 'level desc, name'

    name = fields.Char(string='Job Title', required=True, tracking=True, index=True)
    
    department_id = fields.Many2one(
        'core.department',
        string='Department',
        tracking=True,
        index=True
    )
    
    parent_id = fields.Many2one(
        'core.job.position',
        string='Parent Job',
        ondelete='restrict',
        index=True,
        tracking=True,
        help='Job position hierarchy (e.g., Director > Manager > Supervisor)'
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('core.job.position', 'parent_id', string='Child Positions')
    
    level = fields.Integer(
        string='Level/Rank',
        default=1,
        tracking=True,
        help='Job level for hierarchy (1=Junior, 5=Director)'
    )
    
    description = fields.Text(string='Job Description')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
    # Statistics
    employee_count = fields.Integer(
        string='Employee Count',
        compute='_compute_employee_count'
    )

    def _compute_employee_count(self):
        employee_data = self.env['core.employee']._read_group(
            [('job_position_id', 'in', self.ids)],
            ['job_position_id'],
            ['__count']
        )
        result = {job.id: count for job, count in employee_data}
        for job in self:
            job.employee_count = result.get(job.id, 0)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise exceptions.ValidationError('You cannot create recursive job positions!')

    def name_get(self):
        result = []
        for job in self:
            name = job.name
            if job.department_id:
                name = f"{job.name} ({job.department_id.name})"
            result.append((job.id, name))
        return result
