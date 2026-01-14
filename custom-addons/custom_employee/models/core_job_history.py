from odoo import models, fields, api, exceptions

class CoreEmployeeJobHistory(models.Model):
    _name = 'core.employee.job.history'
    _description = 'Employee Job History'
    _order = 'start_date desc, id desc'
    _rec_name = 'job_position_id'

    employee_id = fields.Many2one(
        'core.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    job_position_id = fields.Many2one(
        'core.job.position',
        string='Job Position',
        required=True,
        index=True
    )
    
    department_id = fields.Many2one(
        'core.department',
        string='Department',
        required=True,
        index=True
    )
    
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today, index=True)
    end_date = fields.Date(string='End Date', index=True)
    
    is_current = fields.Boolean(
        string='Is Current',
        compute='_compute_is_current',
        store=True,
        index=True
    )
    
    notes = fields.Text(string='Notes')

    @api.depends('end_date')
    def _compute_is_current(self):
        for record in self:
            record.is_current = not record.end_date

    @api.constrains('employee_id', 'is_current')
    def _check_unique_current(self):
        """Ensure only one current job history record per employee"""
        for record in self:
            if record.is_current:
                existing = self.search([
                    ('employee_id', '=', record.employee_id.id),
                    ('is_current', '=', True),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise exceptions.ValidationError(
                        'An employee can only have one current job history record. '
                        'Please close the previous record before creating a new one.'
                    )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.start_date > record.end_date:
                raise exceptions.ValidationError('End date cannot be before start date!')
