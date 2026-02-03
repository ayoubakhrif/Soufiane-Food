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
    
    # New Site Fields
    hours_mediouna = fields.Float(string='Heures Mediouna', compute='_compute_salary_details', store=True)
    salary_mediouna = fields.Float(string='Salaire Mediouna', compute='_compute_salary_details', store=True)
    hours_casa = fields.Float(string='Heures Casa', compute='_compute_salary_details', store=True)
    salary_casa = fields.Float(string='Salaire Casa', compute='_compute_salary_details', store=True)

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

    def _check_attendance_coverage(self):
        """
        Verify that for every working day in the month,
        there is either an attendance record or an approved leave.
        """
        config = self.env['custom.attendance.config'].get_main_config()
        non_working_day = int(config.non_working_day) if config else 6
        # Robust date conversion for holidays
        holiday_dates = [fields.Date.to_date(d) for d in config.public_holiday_ids.mapped('date')] if config else []

        for rec in self:
            if not rec.employee_id or not rec.month or not rec.year:
                continue

            try:
                m = int(rec.month)
                y = rec.year
                num_days = calendar.monthrange(y, m)[1]
                start_date = date(y, m, 1)
                end_date = date(y, m, num_days)
            except:
                continue

            # 1. Fetch all attendances for this employee in this month
            attendances = self.env['custom.attendance.search']([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ]) if hasattr(self.env['custom.attendance'], 'search') else self.env['custom.attendance'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ])
            # Note: The search call above is standard. Just keeping it simple.
            
            attendances = self.env['custom.attendance'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ])

            # Robust date conversion for attendances
            attended_dates = {fields.Date.to_date(d) for d in attendances.mapped('date')}

            # 2. Fetch all approved leaves overlapping this month
            leaves = self.env['custom.leave'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approved'),
                ('date_from', '<=', end_date),
                ('date_to', '>=', start_date)
            ])
            
            leave_covered_dates = set()
            for leave in leaves:
                # Calculate intersection of leave range and current month
                l_start = max(leave.date_from, start_date)
                l_end = min(leave.date_to, end_date)
                
                curr = l_start
                while curr <= l_end:
                    if curr.weekday() != non_working_day and curr not in holiday_dates:
                        leave_covered_dates.add(curr)
                    curr += timedelta(days=1)


            # 3. Iterate over expected working days
            missing_days = []
            for day in range(1, num_days + 1):
                current_date = date(y, m, day)
                
                # Skip non-working days (e.g. Sunday)
                if current_date.weekday() == non_working_day:
                    continue
                
                # Skip public holidays
                if current_date in holiday_dates:
                    continue
                
                # Check coverage
                if current_date not in attended_dates and current_date not in leave_covered_dates:
                    missing_days.append(current_date)

            if missing_days:
                days_str = ", ".join([d.strftime('%Y-%m-%d') for d in missing_days])
                raise exceptions.ValidationError(
                    f"La présence de ces jours là n'est pas rentré: {days_str}"
                )

    @api.model
    def create(self, vals):
        record = super(CustomMonthlySalary, self).create(vals)
        # record._check_attendance_coverage() # Defer to validate
        return record

    def write(self, vals):
        # Allow system updates (superuser) OR Admins to bypass this check
        if not self.env.su and not self.env.user.has_group('custom_attendance.group_custom_attendance_admin'):
            for rec in self:
                if rec.state == 'validated' and 'state' not in vals:
                     raise exceptions.UserError("Impossible de modifier un bulletin de salaire validé.")
        
        res = super(CustomMonthlySalary, self).write(vals)
        # if 'employee_id' in vals or 'month' in vals or 'year' in vals:
        #      self._check_attendance_coverage() # Defer to validate
        return res

    @api.depends('employee_id', 'month', 'year')
    def _compute_salary_details(self):
        config = self.env['custom.attendance.config'].get_main_config()
        non_working_day = int(config.non_working_day) if config else 6
        daily_hours = config.working_hours_per_day if config else 8.0
        ot_coeff = config.overtime_coefficient if config else 1.0
        
        # Robust date conversion for holidays
        holiday_dates = [fields.Date.to_date(d) for d in config.public_holiday_ids.mapped('date')] if config else []

        for rec in self:
            if not rec.employee_id or not rec.month or not rec.year:
                rec.working_days_count = 0
                rec.hourly_salary = 0.0
                rec.total_normal_hours = 0.0
                rec.total_missing_hours = 0.0
                rec.total_overtime_hours = 0.0
                rec.total_holiday_hours = 0.0
                rec.hours_mediouna = 0.0
                rec.salary_mediouna = 0.0
                rec.hours_casa = 0.0
                rec.salary_casa = 0.0
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
                    
                    if wd != non_working_day:
                        working_days += 1
                        
                rec.working_days_count = working_days
            except:
                rec.working_days_count = 0
            
            # Hourly Rate
            total_expected_hours = rec.working_days_count * daily_hours
            rec.hourly_salary = (rec.base_salary / total_expected_hours) if total_expected_hours else 0.0
            rate = rec.hourly_salary

            # --- Data Fetching & Site Split ---
            start_date = date(y, m, 1)
            end_date = date(y, m, num_days)
            
            domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ]
            
            # Group By Site, IsAbsent, AbsenceType
            groups = self.env['custom.attendance'].read_group(
                domain,
                ['site', 'is_absent', 'absence_type', 'normal_working_hours', 'missing_hours', 'overtime_hours', 'holiday_hours'],
                ['site', 'is_absent', 'absence_type'],
                lazy=False
            )

            t_normal = 0.0
            t_missing = 0.0
            t_overtime = 0.0
            t_holiday = 0.0
            
            # Site accumulators
            h_med = 0.0
            s_med = 0.0
            h_casa = 0.0
            s_casa = 0.0
            
            payroll_site = rec.employee_id.payroll_site # mediouna or casa
            
            # --- Fixed Holiday Bonus Logic ---
            # Calculate number of public holidays in this month
            num_holidays = 0
            for h_date in holiday_dates:
                 if start_date <= h_date <= end_date:
                     num_holidays += 1
            
            fixed_holiday_hours = num_holidays * daily_hours
            fixed_holiday_amount = fixed_holiday_hours * rate
            
            # Add to initial site accumulators based on payroll_site
            if payroll_site == 'mediouna':
                h_med += fixed_holiday_hours
                s_med += fixed_holiday_amount
            else:
                h_casa += fixed_holiday_hours
                s_casa += fixed_holiday_amount
                
            t_holiday += fixed_holiday_hours

            for g in groups:
                site = g['site']
                is_absent = g['is_absent']
                abs_type = g['absence_type']
                
                # Raw sums from attendance
                g_norm = g['normal_working_hours']
                g_miss = g['missing_hours']
                g_over = g['overtime_hours']
                g_holi = g['holiday_hours']
                count = g['__count'] # record count - FIXED from site_count
                
                t_normal += g_norm
                t_missing += g_miss
                t_overtime += g_over
                t_holiday += g_holi
                
                # Allocation Logic
                target_site = site
                cost = 0.0
                hours_to_add = 0.0
                
                if not is_absent:
                    # Normal Day
                    # Hours = Normal + Overtime + Holiday
                    hours_to_add = g_norm + g_over + g_holi
                    # Cost = Normal*1 + Overtime*Coeff + Holiday*2 - Missing*1
                    cost = (g_norm * 1) + (g_over * ot_coeff) + (g_holi * 2) - (g_miss * 1)
                    cost *= rate
                    
                else:
                    # Absent Day
                    target_site = payroll_site # Force correct site
                    if abs_type == 'leave':
                        # Consumed Leave -> 8 hours paid
                        added_h = daily_hours * count
                        hours_to_add = added_h
                        cost = added_h * rate
                        
                    elif abs_type == 'deduction':
                        # Deduction -> Reduce salary
                        deduction = g_miss * rate
                        cost = -deduction
                        hours_to_add = 0.0
                
                # Accumulate
                if target_site == 'mediouna':
                    h_med += hours_to_add
                    s_med += cost
                elif target_site == 'casa':
                    h_casa += hours_to_add
                    s_casa += cost
                elif not target_site and not is_absent:
                     if payroll_site == 'mediouna':
                         h_med += hours_to_add
                         s_med += cost
                     else:
                         h_casa += hours_to_add
                         s_casa += cost

            rec.total_normal_hours = t_normal
            rec.total_missing_hours = t_missing
            rec.total_overtime_hours = t_overtime
            rec.total_holiday_hours = t_holiday
            
            rec.hours_mediouna = h_med
            rec.salary_mediouna = s_med
            rec.hours_casa = h_casa
            rec.salary_casa = s_casa

    @api.depends('salary_mediouna', 'salary_casa')
    def _compute_final_salary(self):
        config = self.env['custom.attendance.config'].get_main_config()
        ot_coeff = config.overtime_coefficient if config else 1.0
        
        for rec in self:
            rec.salary_mediouna = round(rec.salary_mediouna, 2)
            rec.salary_casa = round(rec.salary_casa, 2)
            
            rec.final_salary = rec.salary_mediouna + rec.salary_casa
            
            # Update legacy fields for display consistency
            rec.deduction_amount = rec.total_missing_hours * rec.hourly_salary
            rec.overtime_amount = rec.total_overtime_hours * rec.hourly_salary * ot_coeff
            rec.holiday_amount = rec.total_holiday_hours * rec.hourly_salary * 2

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
            # Check coverage now
            rec._check_attendance_coverage()
            attendances.write({'state': 'locked'})

    def unlink(self):
        # Allow system updates (superuser) OR Admins to bypass this check
        if not self.env.su and not self.env.user.has_group('custom_attendance.group_custom_attendance_admin'):
            for rec in self:
                if rec.state == 'validated':
                    raise exceptions.UserError("Impossible de supprimer un bulletin de salaire validé.")
        return super(CustomMonthlySalary, self).unlink()