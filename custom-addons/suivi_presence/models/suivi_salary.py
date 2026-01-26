from odoo import models, fields, api, exceptions
from datetime import date, timedelta
import calendar
import logging

_logger = logging.getLogger(__name__)

class SuiviSalary(models.Model):
    _name = 'suivi.salary'
    _description = 'Bulletin de Salaire (Suivi)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one('suivi.employee', string='Employé', required=True, ondelete='cascade')
    month = fields.Selection([
        ('1', 'Janvier'), ('2', 'Février'), ('3', 'Mars'), ('4', 'Avril'),
        ('5', 'Mai'), ('6', 'Juin'), ('7', 'Juillet'), ('8', 'Aout'),
        ('9', 'Septembre'), ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre')
    ], string='Mois', required=True, default=lambda self: str(date.today().month))
    year = fields.Integer(string='Année', required=True, default=lambda self: date.today().year)

    base_salary = fields.Float(string='Salaire de base', readonly=True)
    working_days_count = fields.Integer(string='Jours de travaille', compute='_compute_salary_details', store=True)
    hourly_salary = fields.Float(string='Salaire horaire', compute='_compute_salary_details', store=True)

    total_normal_hours = fields.Float(string='Heures Normales', compute='_compute_salary_details', store=True)
    total_missing_hours = fields.Float(string='Heures Manquantes', compute='_compute_salary_details', store=True)
    total_overtime_hours = fields.Float(string='Heures Supp.', compute='_compute_salary_details', store=True)
    total_holiday_hours = fields.Float(string='Heures Fériés', compute='_compute_salary_details', store=True)

    # Site Split
    hours_mediouna = fields.Float(string='Heures Mediouna', compute='_compute_salary_details', store=True)
    salary_mediouna = fields.Float(string='Salaire Mediouna', compute='_compute_salary_details', store=True)
    hours_casa = fields.Float(string='Heures Casa', compute='_compute_salary_details', store=True)
    salary_casa = fields.Float(string='Salaire Casa', compute='_compute_salary_details', store=True)

    final_salary = fields.Float(string='Salaire Final', compute='_compute_final_salary', store=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validé')
    ], default='draft', string='Status')

    _sql_constraints = [
        ('unique_employee_month_year', 'unique(employee_id, month, year)', 'Bulletin déjà existant.')
    ]

    @api.depends('employee_id', 'month', 'year')
    def _compute_salary_details(self):
        config = self.env['suivi.presence.config'].get_main_config()
        daily_hours = config.working_hours_per_day if config else 8.0
        non_working_day = int(config.non_working_day) if config else 6
        holidays_map = {h.date: h.name for h in config.public_holiday_ids} if config else {}

        for rec in self:
            if not rec.employee_id or not rec.month:
                continue

            try:
                m = int(rec.month)
                y = rec.year
                num_days = calendar.monthrange(y, m)[1]
                start_date = date(y, m, 1)
                end_date = date(y, m, num_days)
            except:
                continue

            # 1. Base Salary Snapshot
            rec.base_salary = rec.employee_id.monthly_salary

            # 2. Working Days Calculation
            working_days = 0
            for day in range(1, num_days + 1):
                d = date(y, m, day)
                if d.weekday() != non_working_day and d not in holidays_map:
                    working_days += 1
            rec.working_days_count = working_days
            
            # Hourly Rate
            expected_total_hours = working_days * daily_hours
            rate = (rec.base_salary / expected_total_hours) if expected_total_hours else 0.0
            rec.hourly_salary = round(rate, 2)

            # 3. Calculate Hours from Presence Pairs
            # 3. Calculate Hours from Presence Pairs
            presences = self.env['suivi.presence'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('datetime', '>=', start_date),
                ('datetime', '<=', end_date + timedelta(days=1)),
            ], order='datetime asc')

            # Group by Day
            day_records = {}
            for p in presences:
                p_date = p.datetime.date()
                if p_date not in day_records:
                    day_records[p_date] = []
                day_records[p_date].append(p)

            t_norm = t_over = t_miss = t_holi = 0.0
            h_med = s_med = h_casa = s_casa = 0.0
            
            # Fetch config
            # Default values if config missing
            off_in_med = config.official_check_in_mediouna if config else 9
            off_out_med = config.official_check_out_mediouna if config else 17
            off_in_casa = config.official_check_in_casa if config else 9.5
            off_out_casa = config.official_check_out_casa if config else 17.5
            
            tolerance_min = config.delay_tolerance if config else 0
            ot_coeff = config.overtime_coefficient if config else 1.0
            
            # Expected hours per day used for Missing calculation
            # We use working_hours_per_day as the target for the day regardless of site mix
            expected_daily = config.working_hours_per_day if config else 8.0

            # A. Process Leaves First
            approved_leaves = self.env['suivi.leave'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approved'),
                ('date_from', '<=', end_date),
                ('date_to', '>=', start_date)
            ])
            paid_leave_days = set()
            unpaid_leave_days = set()
            
            for l in approved_leaves:
                if not l.date_from or not l.date_to:
                    continue
                curr = max(l.date_from, start_date)
                lend = min(l.date_to, end_date)
                while curr <= lend:
                    if l.leave_type == 'paid':
                        paid_leave_days.add(curr)
                    else:
                        unpaid_leave_days.add(curr)
                    curr += timedelta(days=1)

            # B. Iterate Days
            for day in range(1, num_days + 1):
                curr_date = date(y, m, day)
                is_holiday = curr_date in holidays_map
                is_off_day = curr_date.weekday() == non_working_day
                
                # If Paid Leave
                if curr_date in paid_leave_days:
                    t_norm += daily_hours 
                    # Pay the leave (Usually credited to Base Site or just general)
                    # For split purposes, we credit to Payroll Site
                    cost = daily_hours * rate
                    if rec.employee_id.payroll_site == 'casa':
                         h_casa += daily_hours
                         s_casa += cost
                    else:
                         h_med += daily_hours
                         s_med += cost
                    continue
                
                # If Unpaid Leave
                if curr_date in unpaid_leave_days:
                    continue

                events = day_records.get(curr_date, [])
                day_normal = 0.0
                
                # Pairing: Entry -> Sortie
                pending_entry = False
                pending_site = False
                
                processed_pairs = []
                for ev in events:
                    if ev.type == 'entree':
                        pending_entry = ev.datetime
                        pending_site = ev.site
                    elif ev.type == 'sortie' and pending_entry:
                        # Use site from Entry
                        processed_pairs.append((pending_entry, ev.datetime, pending_site))
                        pending_entry = False
                
                for (start_dt, end_dt, p_site) in processed_pairs:
                    import pytz
                    user_tz = pytz.timezone('Africa/Casablanca')
                    # Odoo Datetime fields are already UTC aware (if not naive)
                    # We simply convert to target timezone
                    local_start = start_dt.astimezone(user_tz)
                    local_end = end_dt.astimezone(user_tz)
                    
                    in_f = local_start.hour + local_start.minute / 60.0
                    out_f = local_end.hour + local_end.minute / 60.0
                    
                    # Determine Applicable Limits based on SITE
                    if p_site == 'casa':
                        c_off_in = off_in_casa
                        c_off_out = off_out_casa
                    else:
                        c_off_in = off_in_med
                        c_off_out = off_out_med

                    pair_cost = 0.0
                    pair_hours = 0.0
                    
                    # Logic 1: Normal with Tolerance & Early Ignore
                    eff_in = in_f
                    
                    if in_f < c_off_in:
                        eff_in = c_off_in
                    else:
                        diff_min = (in_f - c_off_in) * 60.0
                        if diff_min > 0 and diff_min <= tolerance_min:
                            eff_in = c_off_in
                    
                    eff_out_norm = min(out_f, c_off_out)
                    dur_norm = max(0, eff_out_norm - eff_in)
                    
                    # Logic 2: Overtime (Strictly after Official Out)
                    over_start = max(in_f, c_off_out)
                    dur_over = max(0, out_f - over_start)

                    if is_off_day or is_holiday:
                        # All is extra
                        raw_dur = (local_end - local_start).total_seconds() / 3600.0
                        
                        if is_holiday:
                            t_holi += raw_dur
                            pair_cost += raw_dur * rate * 2 # Holiday Rate
                        else:
                            t_over += raw_dur
                            pair_cost += raw_dur * rate * ot_coeff # Overtime Rate
                        
                        pair_hours += raw_dur
                    else:
                        # Normal Day
                        t_norm += dur_norm
                        t_over += dur_over
                        day_normal += dur_norm
                        
                        pair_hours += (dur_norm + dur_over)
                        pair_cost += (dur_norm * rate) + (dur_over * rate * ot_coeff)

                    # Attribute to Site
                    if p_site == 'casa':
                        h_casa += pair_hours
                        s_casa += pair_cost
                    else:
                        h_med += pair_hours
                        s_med += pair_cost

                # Missing Calculation (Per Day)
                # We compare day_normal against expected_daily (global target)
                if not is_off_day and not is_holiday:
                    if day_normal < expected_daily:
                        miss = expected_daily - day_normal
                        t_miss += miss
                        # Deduct from salary? 
                        # 'suivi.salary' usually validates total pay. 
                        # If we track 's_med' and 's_casa' as *earned* salary, then missing hours simply result in less money earned.
                        # No explicit deduction needed unless we started from a full monthly salary.
                        # BUT: The base salary is likely a fixed monthly amount. 
                        # Converting to hourly 'rate' implies we pay per hour? 
                        # Request says: "shows the salary of hours worked in Casa...".
                        # If we just sum earned, we are good.
                        # But wait, `pay_normal` in `_compute_final_salary` uses `rec.total_normal_hours * rate`.
                        # If `t_norm` is low, pay is low. Correct.

            rec.total_normal_hours = round(t_norm, 2)
            rec.total_overtime_hours = round(t_over, 2)
            rec.total_holiday_hours = round(t_holi, 2)
            rec.total_missing_hours = round(t_miss, 2)
            
            rec.hours_mediouna = round(h_med, 2)
            rec.salary_mediouna = round(s_med, 2)
            rec.hours_casa = round(h_casa, 2)
            rec.salary_casa = round(s_casa, 2)

    total_advances = fields.Float(string='Avances', compute='_compute_final_salary', store=True)

    @api.depends('total_normal_hours', 'total_overtime_hours', 'total_holiday_hours', 'total_missing_hours')
    def _compute_final_salary(self):
        config = self.env['suivi.presence.config'].get_main_config()
        ot_coeff = config.overtime_coefficient if config else 1.0
        
        for rec in self:
            # 1. Base Salary from Hours (Splits)
            gross_salary = rec.salary_mediouna + rec.salary_casa
            
            # 2. Calculate Advances
            domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'confirmed'),
                ('month', '=', rec.month),
                ('year', '=', rec.year)
            ]
            advances = self.env['suivi.salary.advance'].search(domain)
            total_adv = sum(advances.mapped('amount'))
            rec.total_advances = total_adv
            
            # 3. Final Net
            rec.final_salary = gross_salary - total_adv

    def action_validate(self):
        for rec in self:
            rec.state = 'validated'
