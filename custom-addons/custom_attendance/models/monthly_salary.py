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
    total_holiday_hours = fields.Float(string='Total des heures fériés', compute='_compute_salary_details', store=True)
    
    overtime_amount = fields.Float(string='Montant supplémentaire', compute='_compute_final_salary', store=True)
    holiday_amount = fields.Float(string='Montant Fériés', compute='_compute_final_salary', store=True)
    deduction_amount = fields.Float(string='Montant déduit', compute='_compute_final_salary', store=True)
    final_salary = fields.Float(string='Salaire final', compute='_compute_final_salary', store=True)
    
    state = fields.Selection([
        ('draft', 'Non payé'),
        ('validated', 'Payé')
    ], default='draft', string='Status', tracking=True)

    _sql_constraints = [
        ('unique_employee_month_year', 'unique(employee_id, month, year)', 
         'Un bulletin de salaire existe déjà pour cet employé, ce mois et cette année.')
    ]

    @api.depends('employee_id', 'month', 'year')
    def _compute_salary_details(self):
        config = self.env['custom.attendance.config'].get_main_config()
        non_working_day = int(config.non_working_day) if config else 6
        daily_hours = config.working_hours_per_day if config else 8.0
        
        # Get holiday dates from config
        holiday_dates = config.public_holiday_ids.mapped('date') if config else []

        for rec in self:
            if not rec.employee_id or not rec.month or not rec.year:
                rec.working_days_count = 0
                rec.hourly_salary = 0.0
                rec.total_normal_hours = 0.0
                rec.total_missing_hours = 0.0
                rec.total_overtime_hours = 0.0
                rec.total_holiday_hours = 0.0
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
                    current_date = date(y, m, day)
                    wd = current_date.weekday()
                    
                    # Exclude non-working days AND public holidays
                    if wd != non_working_day and current_date not in holiday_dates:
                        working_days += 1
                        
                rec.working_days_count = working_days
            except:
                rec.working_days_count = 0
            
            # Hourly Rate
            total_expected_hours = rec.working_days_count * daily_hours
            rec.hourly_salary = (rec.base_salary / total_expected_hours) if total_expected_hours else 0.0

            # Optimisation: read_group
            start_date = date(y, m, 1)
            end_date = date(y, m, num_days)
            
            domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ]
            
            data = self.env['custom.attendance'].read_group(
                domain,
                ['normal_working_hours', 'missing_hours', 'overtime_hours', 'holiday_hours'],
                []
            )
            
            if data:
                rec.total_normal_hours = data[0]['normal_working_hours']
                rec.total_missing_hours = data[0]['missing_hours']
                rec.total_overtime_hours = data[0]['overtime_hours']
                rec.total_holiday_hours = data[0]['holiday_hours']
            else:
                rec.total_normal_hours = 0.0
                rec.total_missing_hours = 0.0
                rec.total_overtime_hours = 0.0
                rec.total_holiday_hours = 0.0

    @api.depends('total_missing_hours', 'total_overtime_hours', 'total_holiday_hours', 'hourly_salary')
    def _compute_final_salary(self):
        config = self.env['custom.attendance.config'].get_main_config()
        ot_coeff = config.overtime_coefficient if config else 1.0
        
        for rec in self:
            rec.deduction_amount = rec.total_missing_hours * rec.hourly_salary
            rec.overtime_amount = rec.total_overtime_hours * rec.hourly_salary * ot_coeff
            rec.holiday_amount = rec.total_holiday_hours * rec.hourly_salary * 2 # Double pay
            rec.final_salary = rec.base_salary - rec.deduction_amount + rec.overtime_amount + rec.holiday_amount

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

    def write(self, vals):
        for rec in self:
            if rec.state == 'validated' and 'state' not in vals:
                 raise exceptions.UserError("Impossible de modifier un bulletin de salaire validé.")
        return super(CustomMonthlySalary, self).write(vals)

    def unlink(self):
        for rec in self:
            if rec.state == 'validated':
                raise exceptions.UserError("Impossible de supprimer un bulletin de salaire validé.")
        return super(CustomMonthlySalary, self).unlink()
