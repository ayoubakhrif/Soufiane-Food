from odoo import models, fields, api, exceptions
import pytz
import re
from datetime import datetime, timedelta, time


class CustomAttendance(models.Model):
    _name = 'custom.attendance'
    _description = 'Daily Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('custom.employee', string='Employés', required=True, tracking=True)

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    
    # Refactored: Simple Char fields for Input
    check_in_time = fields.Char(string='H.entrée (HH:MM)', tracking=True)
    check_out_time = fields.Char(string='H.sortie (HH:MM)', tracking=True)
    
    # Refactored: Readonly Datetime fields for Storage/Calculation
    check_in = fields.Datetime(string='Heure entrée (Système)', readonly=True)
    check_out = fields.Datetime(string='Heure de sortie (Système)', readonly=True)
    
    delay_minutes = fields.Integer(string='Retard (Minutes)', compute='_compute_hours', store=True)
    missing_hours = fields.Float(string='Heures manquantes', compute='_compute_hours', store=True)
    overtime_hours = fields.Float(string='Heures supplémentaires', compute='_compute_hours', store=True)
    holiday_hours = fields.Float(string='Heures Fériés', compute='_compute_hours', store=True)
    normal_working_hours = fields.Float(string='Heures normales', compute='_compute_hours', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('locked', 'Locked')
    ], default='draft', string='Status', tracking=True)

    # Site Fields
    site = fields.Selection([
        ('mediouna', 'Mediouna'),
        ('casa', 'Casa')
    ], string='Site', compute='_compute_site_default', store=True, readonly=False)
    
    is_absent = fields.Boolean(string='Absent', default=False, tracking=True)
    absence_type = fields.Selection([
        ('deduction', 'Déduit du salaire'),
        ('leave', 'Consomme un jour de congé')
    ], string="Type d'absence")
    
    employee_payroll_site = fields.Selection(related='employee_id.payroll_site', string="Site de Paie (Tech)", readonly=True)

    @api.depends('employee_id.payroll_site')
    def _compute_site_default(self):
        for rec in self:
            if rec.employee_id.payroll_site == 'casa':
                rec.site = 'casa'
            elif not rec.site and rec.employee_id.payroll_site == 'mediouna':
                rec.site = 'mediouna'

    def action_set_absent(self):
        for rec in self:
            rec.is_absent = True
            rec.check_in = False
            rec.check_out = False

    def action_set_present(self):
        for rec in self:
            rec.is_absent = False
            rec.absence_type = False

    _sql_constraints = [
        ('unique_employee_date', 'unique(employee_id, date)', 'Chaque employé soit avoire une seule fiche de présence par jour!')
    ]

    @api.constrains('check_in_time', 'check_out_time')
    def _check_time_format(self):
        pattern = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')
        for rec in self:
            if rec.check_in_time and not pattern.match(rec.check_in_time):
                raise exceptions.ValidationError("Format d'heure d'entrée invalide (HH:MM attendu).")
            if rec.check_out_time and not pattern.match(rec.check_out_time):
                raise exceptions.ValidationError("Format d'heure de sortie invalide (HH:MM attendu).")

    # ---------------------------------------------------------
    # Helper: Time Conversion
    # ---------------------------------------------------------
    def _get_utc_time(self, date_val, time_str):
        """
        Converts Date + HH:MM String into UTC Datetime.
        Uses 'Africa/Casablanca' as the reference timezone.
        """
        if not date_val or not time_str:
            return False
            
        tz_name = 'Africa/Casablanca'
        try:
            user_tz = pytz.timezone(tz_name)
        except:
            user_tz = pytz.utc
            
        try:
            h, m = map(int, time_str.split(':'))
            # Combine date + time (naive)
            naive_dt = datetime.combine(date_val, time(h, m))
            # Localize to Casablanca
            local_dt = user_tz.localize(naive_dt)
            # Convert to UTC and strip tzinfo for Odoo storage
            return local_dt.astimezone(pytz.utc).replace(tzinfo=None)
        except:
            return False

    # ---------------------------------------------------------
    # CRUD Overrides: The Core Logic
    # ---------------------------------------------------------
    
    @api.model
    def create(self, vals):
        # Handle Time Conversion on Creation
        if 'date' in vals:
             date_val = fields.Date.from_string(vals['date'])
             
             if vals.get('check_in_time'):
                 vals['check_in'] = self._get_utc_time(date_val, vals['check_in_time'])
             
             if vals.get('check_out_time'):
                 vals['check_out'] = self._get_utc_time(date_val, vals['check_out_time'])

        rec = super(CustomAttendance, self).create(vals)
        rec._handle_absence_leave_creation()
        return rec

    def write(self, vals):
        # Handle Time Conversion on Write
        # We need to handle cases where date changes OR time changes
        for rec in self:
            # Determine effective date
            effective_date = rec.date
            if 'date' in vals:
                effective_date = fields.Date.from_string(vals['date'])
            
            updates = {}
            
            # Check In Logic
            if 'check_in_time' in vals:
                # User changed time
                updates['check_in'] = self._get_utc_time(effective_date, vals['check_in_time'])
            elif 'date' in vals and rec.check_in_time:
                # User changed date, recompute existing time
                updates['check_in'] = self._get_utc_time(effective_date, rec.check_in_time)
                
            # Check Out Logic
            if 'check_out_time' in vals:
                updates['check_out'] = self._get_utc_time(effective_date, vals['check_out_time'])
            elif 'date' in vals and rec.check_out_time:
                updates['check_out'] = self._get_utc_time(effective_date, rec.check_out_time)
            
            if updates:
                super(CustomAttendance, rec).write(updates)

        res = super(CustomAttendance, self).write(vals)
        
        for rec in self:
            if 'is_absent' in vals or 'absence_type' in vals:
                rec._handle_absence_leave_creation()
        
        return res

    # ---------------------------------------------------------
    # Logic
    # ---------------------------------------------------------

    @api.depends('check_in', 'check_out', 'employee_id', 'date', 'is_absent')
    def _compute_hours(self):
        config = self.env['custom.attendance.config'].get_main_config()
        if not config:
            off_in_float = 9.5
            off_out_float = 17.5
            daily_hours = 8.0
            tolerance = 0
            holidays = []
            non_working_day = 6
        else:
            off_in_float = config.official_check_in
            off_out_float = config.official_check_out
            daily_hours = config.working_hours_per_day
            tolerance = config.delay_tolerance
            holidays = config.public_holiday_ids.mapped('date')
            non_working_day = int(config.non_working_day)

        tz_name = 'Africa/Casablanca'
        try:
            user_tz = pytz.timezone(tz_name)
        except:
            user_tz = pytz.utc

        for rec in self:
            rec.normal_working_hours = 0.0
            rec.missing_hours = 0.0
            rec.overtime_hours = 0.0
            rec.holiday_hours = 0.0
            rec.delay_minutes = 0

            # A. Exemptions
            if rec.is_absent:
                rec.missing_hours = daily_hours
                continue

            leave_domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approved'),
                ('date_from', '<=', rec.date),
                ('date_to', '>=', rec.date),
            ]
            if self.env['custom.leave'].search_count(leave_domain) > 0:
                rec.normal_working_hours = daily_hours
                continue

            if rec.date.weekday() == non_working_day:
                continue

            if rec.date in holidays:
                if rec.check_in and rec.check_out:
                    duration = (rec.check_out - rec.check_in).total_seconds() / 3600.0
                    rec.holiday_hours = max(0.0, duration)
                    rec.normal_working_hours = rec.holiday_hours
                continue

            # B. Calculation
            if not rec.check_in or not rec.check_out:
                rec.missing_hours = daily_hours
                continue

            c_in_utc = pytz.utc.localize(rec.check_in)
            c_out_utc = pytz.utc.localize(rec.check_out)
            
            c_in_local = c_in_utc.astimezone(user_tz)
            c_out_local = c_out_utc.astimezone(user_tz)

            def get_dt(target_date, float_hour):
                hours = int(float_hour)
                minutes = int((float_hour - hours) * 60)
                naive_dt = datetime.combine(target_date, time(hours, minutes))
                return user_tz.localize(naive_dt)

            off_in_local = get_dt(rec.date, off_in_float)
            off_out_local = get_dt(rec.date, off_out_float)

            # Delay
            if c_in_local > off_in_local:
                diff_minutes = (c_in_local - off_in_local).total_seconds() / 60.0
                if diff_minutes > tolerance:
                    rec.delay_minutes = int(diff_minutes)
            else:
                rec.delay_minutes = 0

            # Normal Hours
            eff_in = max(c_in_local, off_in_local)
            eff_out = min(c_out_local, off_out_local)

            if eff_out > eff_in:
                w_sec = (eff_out - eff_in).total_seconds()
                rec.normal_working_hours = w_sec / 3600.0
            else:
                rec.normal_working_hours = 0.0

            # Missing
            rec.missing_hours = max(0.0, daily_hours - rec.normal_working_hours)

            # Overtime (Evening only)
            if c_out_local > off_out_local:
                rec.overtime_hours = (c_out_local - off_out_local).total_seconds() / 3600.0
            else:
                rec.overtime_hours = 0.0

    def _handle_absence_leave_creation(self):
        for rec in self:
            if rec.is_absent and rec.absence_type == 'leave':
                existing_leave = self.env['custom.leave'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('date_from', '=', rec.date),
                    ('date_to', '=', rec.date),
                    ('leave_type', '=', 'paid')
                ])
                if not existing_leave:
                    if rec.employee_id.leaves_remaining < 1:
                        raise exceptions.ValidationError("Pas de solde de congé restant")
                    
                    self.env['custom.leave'].create({
                        'employee_id': rec.employee_id.id,
                        'date_from': rec.date,
                        'date_to': rec.date,
                        'leave_type': 'paid',
                        'reason': 'Absence marquée depuis la fiche de présence',
                        'state': 'approved'
                    })
