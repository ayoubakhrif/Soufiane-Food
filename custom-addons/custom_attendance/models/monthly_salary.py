from odoo import models, fields, api, exceptions
from datetime import date, timedelta
import calendar

class CustomMonthlySalary(models.Model):
    _name = 'custom.monthly.salary'
    _description = 'Monthly Salary Calculation'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one('custom.employee', string='Employee', required=True)
    month = fields.Selection([
        ('1', 'Janvier'), ('2', 'Février'), ('3', 'Mars'), ('4', 'Avril'),
        ('5', 'Mai'), ('6', 'Juin'), ('7', 'Juillet'), ('8', 'Aout'),
        ('9', 'Septembre'), ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre')
    ], string='Month', required=True, default=lambda self: str(date.today().month))
    year = fields.Integer(string='Année', required=True, default=lambda self: date.today().year)
    
    base_salary = fields.Float(string='Salaire de base', readonly=True)
    working_days_count = fields.Integer(string='Jours de travaille', compute='_compute_salary_details', store=True)
    hourly_salary = fields.Float(string='Salaire par heure', compute='_compute_salary_details', store=True)
    
    total_normal_hours = fields.Float(string='Total des heures normaux', compute='_compute_salary_details', store=True)
    total_missing_hours = fields.Float(string='Total des heures manquantes', compute='_compute_salary_details', store=True)
    total_overtime_hours = fields.Float(string='Total des heures supplémentaires', compute='_compute_salary_details', store=True)
    
    overtime_amount = fields.Float(string='Montant supplémentaire', compute='_compute_final_salary', store=True)
    deduction_amount = fields.Float(string='Montant déduit', compute='_compute_final_salary', store=True)
    final_salary = fields.Float(string='Salaire final', compute='_compute_final_salary', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated')
    ], default='draft', string='Status', tracking=True)

    @api.depends('employee_id', 'month', 'year')
    def _compute_salary_details(self):
        config = self.env['custom.attendance.config'].get_main_config()
        non_working_day = int(config.non_working_day) if config else 6
        daily_hours = config.working_hours_per_day if config else 8.0

        for rec in self:
            if not rec.employee_id or not rec.month or not rec.year:
                continue

            # Snap base salary
            rec.base_salary = rec.employee_id.monthly_salary
            
            # Calculate Working Days in Month
            try:
                m = int(rec.month)
                y = rec.year
                num_days = calendar.monthrange(y, m)[1]
                working_days = 0
                for day in range(1, num_days + 1):
                    wd = date(y, m, day).weekday()
                    if wd != non_working_day:
                        working_days += 1
                rec.working_days_count = working_days
            except:
                rec.working_days_count = 0
            
            # Hourly Rate
            total_expected_hours = rec.working_days_count * daily_hours
            rec.hourly_salary = (rec.base_salary / total_expected_hours) if total_expected_hours else 0.0

            # Fetch Attendances
            start_date = date(y, m, 1)
            end_date = date(y, m, num_days)
            attendances = self.env['custom.attendance'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ])
            
            rec.total_normal_hours = sum(attendances.mapped('normal_working_hours'))
            rec.total_missing_hours = sum(attendances.mapped('missing_hours'))
            rec.total_overtime_hours = sum(attendances.mapped('overtime_hours'))

    @api.depends('total_missing_hours', 'total_overtime_hours', 'hourly_salary')
    def _compute_final_salary(self):
        config = self.env['custom.attendance.config'].get_main_config()
        ot_coeff = config.overtime_coefficient if config else 1.0
        
        for rec in self:
            rec.deduction_amount = rec.total_missing_hours * rec.hourly_salary
            rec.overtime_amount = rec.total_overtime_hours * rec.hourly_salary * ot_coeff
            rec.final_salary = rec.base_salary - rec.deduction_amount + rec.overtime_amount

    def action_validate(self):
        for rec in self:
            rec.state = 'validated'
            # Lock attendances
            m = int(rec.month)
            y = rec.year
            num_days = calendar.monthrange(y, m)[1]
            start_date = date(y, m, 1)
            end_date = date(y, m, num_days)
            attendances = self.env['custom.attendance'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ])
            attendances.write({'state': 'locked'})
