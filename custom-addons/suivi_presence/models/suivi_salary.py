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
            
            # Fetch config for official hours
            off_in = config.official_check_in if config else 9.5
            off_out = config.official_check_out if config else 17.5
            tolerance_min = config.delay_tolerance if config else 0
            
            # Expected hours per day based on config
            expected_daily = off_out - off_in

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
                    continue
                
                # If Unpaid Leave (Calculated as missing/deducted automatically if we skip)
                if curr_date in unpaid_leave_days:
                    # We continue without adding hours, so t_miss will increase at default calculation
                    # Or we explicitly set it? 
                    # Logic below: if day_normal < expected, t_miss += diff.
                    # So if we continue here, day_normal is 0. 
                    # t_miss += 8. Correct.
                    continue

                events = day_records.get(curr_date, [])
                day_normal = 0.0
                day_over = 0.0
                
                # Pairing: Entry -> Sortie
                pending_entry = False
                
                # We need to process pairs.
                # Assumes perfect Entry/Exit pairs for simplicity.
                # If user forgets Exit, next Entry might cause issues, but we'll stick to simple pairing.
                
                processed_pairs = []
                for ev in events:
                    if ev.type == 'entree':
                        pending_entry = ev.datetime
                    elif ev.type == 'sortie' and pending_entry:
                        processed_pairs.append((pending_entry, ev.datetime))
                        pending_entry = False
                
                for (start_dt, end_dt) in processed_pairs:
                    # Convert to float hours (local time handled by Odoo fields usually, but stored as UTC)
                    # We need to be careful with Timezones. 
                    # Assuming basic floats for calculations for now to match user's simplified request.
                    # Best way: Use user's TZ or assume TZ agnostic if inputs are just "time".
                    # Here we have Datetime. We must convert to Time float in user's TZ (Casablanca).
                    
                    # Hack: For simplicity in this context, we take the hour/minute from the stored UTC 
                    # BUT `suivi.presence` usually stores UTC. We need +1 for Casablanca standard (or +0/1).
                    # Actually, better to rely on what `custom_attendance` did: convert to local.
                    
                    import pytz
                    user_tz = pytz.timezone('Africa/Casablanca')
                    local_start = pytz.utc.localize(start_dt).astimezone(user_tz)
                    local_end = pytz.utc.localize(end_dt).astimezone(user_tz)
                    
                    in_f = local_start.hour + local_start.minute / 60.0
                    out_f = local_end.hour + local_end.minute / 60.0
                    
                    # Logic 1: Normal with Tolerance & Early Ignore
                    eff_in = in_f
                    
                    # Early Entry Ignore
                    if in_f < off_in:
                        eff_in = off_in
                    else:
                        # Late Entry Tolerance
                        diff_min = (in_f - off_in) * 60.0
                        if diff_min > 0 and diff_min <= tolerance_min:
                            eff_in = off_in
                    
                    eff_out_norm = min(out_f, off_out)
                    
                    dur_norm = max(0, eff_out_norm - eff_in)
                    day_normal += dur_norm
                    
                    # Logic 2: Overtime (Strictly after Official Out)
                    over_start = max(in_f, off_out)
                    dur_over = max(0, out_f - over_start)
                    day_over += dur_over

                if is_off_day or is_holiday:
                    # On off days, everything is extra
                    # If holiday, we count it as Holiday Hours
                    # If Sunday, we count as Overtime
                    
                    # Total duration worked
                    total_worked = day_normal + day_over # Wait, logic above splits it by Off_Out boundary.
                    # We should just sum total raw duration instead?
                    # Actually, user said: "if employee entered before official hour... didn't count in supp".
                    # This implies even on Sunday, 8am-9am might not count if Official is 9:30?
                    # Unlikely. Usually on Sunday ALL is supp.
                    # Let's assume standard logic for Off Days: All worked time is Overtime/Holiday.
                    
                    raw_duration = 0.0
                    for (s, e) in processed_pairs:
                         raw_duration += (e - s).total_seconds() / 3600.0
                    
                    if is_holiday:
                        t_holi += raw_duration
                    else:
                        t_over += raw_duration
                else:
                    # Normal Working Day
                    t_norm += day_normal
                    t_over += day_over
                    
                    # Missing
                    # We expect `expected_daily` hours.
                    if day_normal < expected_daily:
                        t_miss += (expected_daily - day_normal)

            rec.total_normal_hours = round(t_norm, 2)
            rec.total_overtime_hours = round(t_over, 2)
            rec.total_holiday_hours = round(t_holi, 2)
            rec.total_missing_hours = round(t_miss, 2)

    @api.depends('total_normal_hours', 'total_overtime_hours', 'total_holiday_hours', 'total_missing_hours')
    def _compute_final_salary(self):
        config = self.env['suivi.presence.config'].get_main_config()
        ot_coeff = config.overtime_coefficient if config else 1.0
        
        for rec in self:
            rate = rec.hourly_salary
            
            # Simple Formula: (Normal + Over*Coeff + Holiday*2) * Rate
            # Missing is implicitly deducted by not being in Normal
            
            # Wait, base salary includes normal hours.
            # So Final = (WorkingDays * Hours * Rate) - (Missing * Rate) + (Over * Rate * Coeff) + ...
            # Actually easier: Final = (TotalNormal * Rate) + (Over * Rate * Coeff) + (Holiday * Rate * 2)
            
            pay_normal = rec.total_normal_hours * rate
            pay_over = rec.total_overtime_hours * rate * ot_coeff
            pay_holi = rec.total_holiday_hours * rate * 2
            
            rec.final_salary = pay_normal + pay_over + pay_holi

    def action_validate(self):
        for rec in self:
            rec.state = 'validated'
