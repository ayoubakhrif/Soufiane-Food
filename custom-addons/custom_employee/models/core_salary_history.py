from odoo import models, fields, api, exceptions

class CoreEmployeeSalaryHistory(models.Model):
    _name = 'core.employee.salary.history'
    _description = 'Employee Salary History'
    _order = 'start_date desc, id desc'

    employee_id = fields.Many2one(
        'core.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    monthly_salary = fields.Float(string='Monthly Salary (Bank)', digits=(16, 2))
    cnss_salary = fields.Float(string='CNSS Salary', digits=(16, 2))
    
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today, index=True)
    end_date = fields.Date(string='End Date', index=True)
    
    is_current = fields.Boolean(
        string='Is Current',
        compute='_compute_is_current',
        store=True,
        index=True
    )
    
    change_reason = fields.Selection([
        ('promotion', 'Promotion'),
        ('annual_increase', 'Annual Increase'),
        ('adjustment', 'Salary Adjustment'),
        ('other', 'Other')
    ], string='Change Reason')
    
    notes = fields.Text(string='Notes')

    @api.depends('end_date')
    def _compute_is_current(self):
        for record in self:
            record.is_current = not record.end_date

    @api.constrains('employee_id', 'is_current')
    def _check_unique_current(self):
        """Ensure only one current salary history record per employee"""
        for record in self:
            if record.is_current:
                existing = self.search([
                    ('employee_id', '=', record.employee_id.id),
                    ('is_current', '=', True),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise exceptions.ValidationError(
                        'An employee can only have one current salary history record. '
                        'Please close the previous record before creating a new one.'
                    )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.start_date > record.end_date:
                raise exceptions.ValidationError('End date cannot be before start date!')
