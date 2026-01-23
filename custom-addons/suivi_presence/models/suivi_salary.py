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
            presences = self.env['suivi.presence'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('datetime', '>=', start_date),
                ('datetime', '<=', end_date + timedelta(days=1)), # Fetch extra for overnight
            ], order='datetime asc')

            # Group by Day
            day_records = {} # { date: [records] }
            for p in presences:
                p_date = p.datetime.date()
                if p_date not in day_records:
                    day_records[p_date] = []
                day_records[p_date].append(p)

            t_norm = t_over = t_miss = t_holi = 0.0

            # Iterate over EXPECTED days to catch missing
            # Also handle holidays separately
            
            # A. Process Leaves First
            approved_leaves = self.env['suivi.leave'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approved'),
                ('date_from', '<=', end_date),
                ('date_to', '>=', start_date)
            ])
            leave_days = set()
            for l in approved_leaves:
                curr = max(l.date_from, start_date)
                lend = min(l.date_to, end_date)
                while curr <= lend:
                    leave_days.add(curr)
                    curr += timedelta(days=1)

            # B. Iterate Days
            for day in range(1, num_days + 1):
                curr_date = date(y, m, day)
                is_holiday = curr_date in holidays_map
                is_off_day = curr_date.weekday() == non_working_day
                
                # If Leave
                if curr_date in leave_days:
                    t_norm += daily_hours # Paid as normal
                    continue

                # Get worked hours for this day
                events = day_records.get(curr_date, [])
                worked_hours = 0.0
                
                # Pairing: Entry -> Sortie
                # We assume sorted asc
                # Stack based approach
                pending_entry = False
                
                for ev in events:
                    if ev.type == 'entree':
                        pending_entry = ev.datetime
                    elif ev.type == 'sortie' and pending_entry:
                        # Diff
                        duration = (ev.datetime - pending_entry).total_seconds() / 3600.0
                        worked_hours += duration
                        pending_entry = False
                
                # Analyze Worked Hours
                if is_off_day or is_holiday:
                    # All work is Extra or Holiday
                    if is_holiday:
                        t_holi += worked_hours
                    else:
                        t_over += worked_hours # Worked on Sunday
                else:
                    # Normal Day
                    if worked_hours >= daily_hours:
                        t_norm += daily_hours
                        t_over += (worked_hours - daily_hours)
                    else:
                        t_norm += worked_hours
                        # Only count as missing if NOT a leave (already checked)
                        t_miss += (daily_hours - worked_hours)

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
