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

    # Organizational Information - NEW STRUCTURED FIELDS
    job_position_id = fields.Many2one(
        'core.job.position',
        string='Job Position',
        tracking=True,
        index=True
    )
    department_id = fields.Many2one(
        'core.department',
        string='Department',
        tracking=True,
        index=True
    )
    
    # Legacy fields (for gradual migration)
    job_title = fields.Char(string='Job Position (Legacy)', tracking=True, help='DEPRECATED: Use job_position_id')
    department = fields.Char(string='Department (Legacy)', tracking=True, help='DEPRECATED: Use department_id')
    
    site = fields.Char(string='Site')
    entry_date = fields.Date(string='Date entrée', tracking=True)
    contract_date = fields.Date(string='Date de contrat', tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    matriculation_cnss = fields.Char(string='Matriculation CNSS', tracking=True)
    matriculation = fields.Char(string='Matriculation', tracking=True)
    document_ids = fields.One2many(
        'core.employee.document',
        'employee_id',
        string='Documents'
    )
    
    # History Tracking
    job_history_ids = fields.One2many(
        'core.employee.job.history',
        'employee_id',
        string='Job History'
    )
    salary_history_ids = fields.One2many(
        'core.employee.salary.history',
        'employee_id',
        string='Salary History'
    )
    current_job_history_id = fields.Many2one(
        'core.employee.job.history',
        string='Current Job History',
        compute='_compute_current_histories',
        store=False
    )
    current_salary_history_id = fields.Many2one(
        'core.employee.salary.history',
        string='Current Salary History',
        compute='_compute_current_histories',
        store=False
    )

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

    def _compute_current_histories(self):
        for employee in self:
            current_job = self.env['core.employee.job.history'].search([
                ('employee_id', '=', employee.id),
                ('is_current', '=', True)
            ], limit=1)
            current_salary = self.env['core.employee.salary.history'].search([
                ('employee_id', '=', employee.id),
                ('is_current', '=', True)
            ], limit=1)
            employee.current_job_history_id = current_job
            employee.current_salary_history_id = current_salary

    def write(self, vals):
        """Override write to auto-create history records when job or salary changes"""
        # Process each employee individually to handle multi-record writes safely
        for employee in self:
            # Track job/department changes
            job_changed = 'job_position_id' in vals or 'department_id' in vals
            if job_changed:
                old_job = employee.job_position_id
                old_dept = employee.department_id
                new_job = vals.get('job_position_id', employee.job_position_id.id)
                new_dept = vals.get('department_id', employee.department_id.id)
                
                # Only create history if values actually changed
                if (new_job != old_job.id or new_dept != old_dept.id) and new_job and new_dept:
                    # Close previous history
                    current_job_history = self.env['core.employee.job.history'].search([
                        ('employee_id', '=', employee.id),
                        ('is_current', '=', True)
                    ])
                    if current_job_history:
                        current_job_history.write({'end_date': fields.Date.today()})
                    
                    # Create new history record
                    self.env['core.employee.job.history'].create({
                        'employee_id': employee.id,
                        'job_position_id': new_job,
                        'department_id': new_dept,
                        'start_date': fields.Date.today(),
                    })
            
            # Track salary changes
            salary_changed = 'monthly_salary' in vals or 'cnss_salary' in vals
            if salary_changed:
                old_monthly = employee.monthly_salary
                old_cnss = employee.cnss_salary
                new_monthly = vals.get('monthly_salary', old_monthly)
                new_cnss = vals.get('cnss_salary', old_cnss)
                
                # Only create history if values actually changed
                if new_monthly != old_monthly or new_cnss != old_cnss:
                    # Close previous history
                    current_salary_history = self.env['core.employee.salary.history'].search([
                        ('employee_id', '=', employee.id),
                        ('is_current', '=', True)
                    ])
                    if current_salary_history:
                        current_salary_history.write({'end_date': fields.Date.today()})
                    
                    # Create new history record
                    self.env['core.employee.salary.history'].create({
                        'employee_id': employee.id,
                        'monthly_salary': new_monthly,
                        'cnss_salary': new_cnss,
                        'start_date': fields.Date.today(),
                    })
        
        # Call parent write
        return super(CoreEmployee, self).write(vals)
