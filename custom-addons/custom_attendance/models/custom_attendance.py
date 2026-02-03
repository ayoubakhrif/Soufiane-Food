from odoo import models, fields, api, exceptions
import pytz
import re
from datetime import datetime, time, timedelta

class CustomAttendance(models.Model):
    _name = 'custom.attendance'
    _description = 'Daily Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('custom.employee', string='Employés', required=True, tracking=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)

    # ==================================================================================
    # 1. USER INPUT (Interface Only)
    # ==================================================================================
    check_in_time = fields.Char(string='H.entrée', tracking=True)
    check_out_time = fields.Char(string='H.sortie', tracking=True)

    # ==================================================================================
    # 2. SOURCE OF TRUTH (Minutes - Integer)
    # ==================================================================================
    check_in_minutes = fields.Integer(string='Entrée (Min)', readonly=True)
    check_out_minutes = fields.Integer(string='Sortie (Min)', readonly=True)

    delay_minutes = fields.Integer(string='Retard (Minutes)', compute='_compute_calculations', store=True)
    normal_minutes = fields.Integer(string='Normal (Minutes)', compute='_compute_calculations', store=True)
    missing_minutes = fields.Integer(string='Manquant (Minutes)', compute='_compute_calculations', store=True)
    overtime_minutes = fields.Integer(string='Supplémen. (Minutes)', compute='_compute_calculations', store=True)
    holiday_minutes = fields.Integer(string='Férié (Minutes)', compute='_compute_calculations', store=True)

    # ==================================================================================
    # 3. DISPLAY & PAYROLL (Floats - Computed from Minutes)
    # ==================================================================================
    # Kept for compatibility with Monthly Salary module
    normal_working_hours = fields.Float(string='Heures normales', compute='_compute_display_hours', store=True)
    missing_hours = fields.Float(string='Heures manquantes', compute='_compute_display_hours', store=True)
    overtime_hours = fields.Float(string='Heures supplémentaires', compute='_compute_display_hours', store=True)
    holiday_hours = fields.Float(string='Heures Fériés', compute='_compute_display_hours', store=True)

    # ==================================================================================
    # 4. LEGACY / CALENDAR SUPPORT (Datetime)
    # ==================================================================================
    # Kept for Calendar views. Read-only, synced from Date + Minutes
    check_in = fields.Datetime(string='Heure entrée (Système)', readonly=True)
    check_out = fields.Datetime(string='Heure de sortie (Système)', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('locked', 'Locked')
    ], default='draft', string='Status', tracking=True)

    # Site Fields (unchanged)
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

    _sql_constraints = [
        ('unique_employee_date', 'unique(employee_id, date)', 'Chaque employé soit avoire une seule fiche de présence par jour!')
    ]

    # ==================================================================================
    # HELPER METHODS
    # ==================================================================================
    
    def _time_to_minutes(self, time_str):
        """ Converts 'HH:MM' string to total minutes (int). Returns None if invalid. """
        if not time_str:
            return None
        try:
            h, m = map(int, time_str.split(':'))
            return h * 60 + m
        except:
            return None

    def _minutes_to_datetime(self, date_val, minutes):
        """ Converts Date + Minutes -> UTC Datetime (via Casablanca TZ). """
        if not date_val or minutes is None:
            return False
            
        tz_name = 'Africa/Casablanca'
        try:
            user_tz = pytz.timezone(tz_name)
        except:
            user_tz = pytz.utc
        
        # Handle overnight (minutes > 1440)
        extra_days = minutes // 1440
        rem_minutes = minutes % 1440
        hours = rem_minutes // 60
        mins = rem_minutes % 60
        
        target_date = date_val + timedelta(days=extra_days)
        
        try:
            naive_dt = datetime.combine(target_date, time(hours, mins))
            local_dt = user_tz.localize(naive_dt)
            return local_dt.astimezone(pytz.utc).replace(tzinfo=None)
        except:
            return False

    @api.constrains('check_in_time', 'check_out_time')
    def _check_time_format(self):
        pattern = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')
        for rec in self:
            if rec.check_in_time and not pattern.match(rec.check_in_time):
                raise exceptions.ValidationError("Format d'heure d'entrée invalide (HH:MM attendu).")
            if rec.check_out_time and not pattern.match(rec.check_out_time):
                raise exceptions.ValidationError("Format d'heure de sortie invalide (HH:MM attendu).")

    # ==================================================================================
    # CORE LOGIC: Create / Write
    # ==================================================================================

    def _sync_minutes_and_datetimes(self, vals, existing_date=None, existing_in_time=None, existing_out_time=None):
        """
        Logic to parse HH:MM -> Minutes and apply Overnight Rule.
        Returns a dict of updates to be merged into vals.
        """
        updates = {}
        
        # Determine effective values
        eff_date = fields.Date.from_string(vals.get('date')) if vals.get('date') else existing_date
        eff_in_str = vals.get('check_in_time', existing_in_time)
        eff_out_str = vals.get('check_out_time', existing_out_time)
        
        # 1. Convert to Minutes
        in_min = self._time_to_minutes(eff_in_str)
        out_min = self._time_to_minutes(eff_out_str)
        
        if in_min is not None:
            updates['check_in_minutes'] = in_min
        else:
             updates['check_in_minutes'] = 0 # Explicit reset if cleared

        if out_min is not None:
            # OVERNIGHT RULE: If out < in, assumne next day (+1440 min)
            if in_min is not None and out_min < in_min:
                out_min += 1440
            updates['check_out_minutes'] = out_min
        else:
            updates['check_out_minutes'] = 0

        # 2. Sync Datetime Fields (for Calendar)
        if in_min is not None:
            updates['check_in'] = self._minutes_to_datetime(eff_date, in_min)
        else:
             updates['check_in'] = False
             
        if out_min is not None:
             updates['check_out'] = self._minutes_to_datetime(eff_date, out_min)
        else:
             updates['check_out'] = False

        return updates

    @api.model
    def create(self, vals):
        # Inject Minute and Datetime calculations into vals
        updates = self._sync_minutes_and_datetimes(
            vals, 
            existing_date=fields.Date.context_today(self),
            existing_in_time=None,
            existing_out_time=None
        )
        vals.update(updates)
        
        rec = super(CustomAttendance, self).create(vals)
        rec._handle_absence_leave_creation()
        return rec

    def write(self, vals):
        # We need to process each record individually if fields affecting calculation change
        if any(f in vals for f in ['date', 'check_in_time', 'check_out_time']):
            for rec in self:
                # Calculate updates based on NEW vals merged with OLD record state
                updates = self._sync_minutes_and_datetimes(
                    vals,
                    existing_date=rec.date,
                    existing_in_time=rec.check_in_time,
                    existing_out_time=rec.check_out_time
                )
                # Apply updates to THIS record via super
                # Note: We can't batch write here easily if updates depend on record state
                # Strategy: update 'vals' merely with what is explicitly passed, 
                # but since we have derived fields, we must write them.
                # Simplest robust way: write derived fields explicitly for this record.
                super(CustomAttendance, rec).write(updates)
        
        # Apply standard write
        res = super(CustomAttendance, self).write(vals)
        for rec in self:
             if 'is_absent' in vals or 'absence_type' in vals:
                 rec._handle_absence_leave_creation()
        return res

    # ==================================================================================
    # BUSINESS CALCULATIONS (Integer Math)
    # ==================================================================================

    @api.depends('check_in_minutes', 'check_out_minutes', 'employee_id', 'date', 'is_absent')
    def _compute_calculations(self):
        config = self.env['custom.attendance.config'].get_main_config()
        
        # 1. Config -> Minutes
        if not config:
            off_in_min = 9 * 60 + 30  # 9:30 = 570
            off_out_min = 17 * 60 + 30 # 17:30 = 1050
            daily_min = 8 * 60        # 480
            tolerance_min = 0
            holidays = []
            non_working_day = 6
        else:
            # Convert float hours to minutes
            off_in_min = int(config.official_check_in * 60)
            off_out_min = int(config.official_check_out * 60)
            daily_min = int(config.working_hours_per_day * 60)
            tolerance_min = int(config.delay_tolerance)
            holidays = config.public_holiday_ids.mapped('date')
            non_working_day = int(config.non_working_day)

        for rec in self:
            # Init
            rec.delay_minutes = 0
            rec.normal_minutes = 0
            rec.missing_minutes = 0
            rec.overtime_minutes = 0
            rec.holiday_minutes = 0

            # A. Exemptions
            if rec.is_absent:
                rec.missing_minutes = daily_min
                continue

            leave_domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approved'),
                ('date_from', '<=', rec.date),
                ('date_to', '>=', rec.date),
            ]
            if self.env['custom.leave'].search_count(leave_domain) > 0:
                rec.normal_minutes = daily_min
                continue

            if rec.date.weekday() == non_working_day:
                continue
            
            # Holiday Logic - REMOVED: Now treated as normal days
            # if rec.date in holidays:
            #     if rec.check_in_minutes and rec.check_out_minutes:
            #         duration = max(0, rec.check_out_minutes - rec.check_in_minutes)
            #         rec.holiday_minutes = duration
            #         rec.normal_minutes = duration # For pay consistency
            #     continue

            # B. Calculation (Integers)
            in_m = rec.check_in_minutes
            out_m = rec.check_out_minutes

            if not in_m or not out_m:
                rec.missing_minutes = daily_min
                continue

            # 1. Normal Work (Intersection with Official Schedule)
            eff_in = max(in_m, off_in_min)
            eff_out = min(out_m, off_out_min)
            
            if eff_out > eff_in:
                rec.normal_minutes = eff_out - eff_in
            else:
                rec.normal_minutes = 0
                
            # 2. Delay (Arrived Late)
            # Logic: If ActualIn > OfficialIn + Tolerance
            if in_m > off_in_min:
                diff = in_m - off_in_min
                if diff > tolerance_min:
                    rec.delay_minutes = diff
            
            # 3. Overtime (Left Late)
            # Logic: Only time AFTER OfficialOut
            if out_m > off_out_min:
                 rec.overtime_minutes = out_m - off_out_min
            
            # 4. Missing
            if rec.date not in holidays:
                rec.missing_minutes = max(0, daily_min - rec.normal_minutes)
            else:
                rec.missing_minutes = 0


    @api.depends('normal_minutes', 'missing_minutes', 'overtime_minutes', 'holiday_minutes')
    def _compute_display_hours(self):
        for rec in self:
            rec.normal_working_hours = round(rec.normal_minutes / 60.0, 2)
            rec.missing_hours = round(rec.missing_minutes / 60.0, 2)
            rec.overtime_hours = round(rec.overtime_minutes / 60.0, 2)
            rec.holiday_hours = round(rec.holiday_minutes / 60.0, 2)


    # ==================================================================================
    # EXTRAS
    # ==================================================================================
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
            rec.check_in_minutes = 0
            rec.check_out_minutes = 0
            rec.check_in = False
            rec.check_out = False

    def action_set_present(self):
        for rec in self:
            rec.is_absent = False
            rec.absence_type = False

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
