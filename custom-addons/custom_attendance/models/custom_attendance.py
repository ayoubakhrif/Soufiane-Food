from odoo import models, fields, api, exceptions
import math
import pytz
from datetime import datetime, timedelta, time


class CustomAttendance(models.Model):
    _name = 'custom.attendance'
    _description = 'Daily Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('custom.employee', string='Employés', required=True, tracking=True)

    def _auto_init(self):
        # 🛠️ Fix: Handle conversion from Float to Datetime manually
        # If check_in is double precision, drop it to let Odoo recreate it as Datetime
        # This prevents "psycopg2.errors.CannotCoerce"
        cr = self.env.cr
        cr.execute("SELECT data_type FROM information_schema.columns WHERE table_name = 'custom_attendance' AND column_name = 'check_in'")
        res = cr.fetchone()
        if res and res[0] == 'double precision':
            cr.execute("ALTER TABLE custom_attendance DROP COLUMN check_in CASCADE")
            cr.execute("ALTER TABLE custom_attendance DROP COLUMN check_out CASCADE")
            
        super()._auto_init()

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    
    check_in = fields.Datetime(string='Heure entrée', required=True, default=fields.Datetime.now)
    check_out = fields.Datetime(string='Heure de sortie', required=True, default=fields.Datetime.now)
    
    delay_minutes = fields.Integer(string='Delay (Minutes)', compute='_compute_hours', store=True)
    missing_hours = fields.Float(string='Heures manquantes', compute='_compute_hours', store=True)
    overtime_hours = fields.Float(string='Heures supplémentaires', compute='_compute_hours', store=True)
    holiday_hours = fields.Float(string='Heures Fériés', compute='_compute_hours', store=True)
    normal_working_hours = fields.Float(string='Heures normales', compute='_compute_hours', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('locked', 'Locked')
    ], default='draft', string='Status', tracking=True)

    # New Fields for Enhancements
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

    @api.constrains('check_in', 'check_out')
    def _check_validity(self):
        for rec in self:
            if rec.check_out < rec.check_in:
                raise exceptions.ValidationError("Heure d'entrée ne peut pas etre supérieure à l'heure de sortie.")

    @api.depends('check_in', 'check_out', 'employee_id', 'date')
    def _compute_hours(self):
        # 1. Get Configuration
        config = self.env['custom.attendance.config'].get_main_config()
        if not config:
            off_in_float = 9.5  # 09:30
            off_out_float = 17.5 # 17:30
            daily_hours = 8.0
            tolerance = 0
            holidays = []
            non_working_day = 6 # Sunday
        else:
            off_in_float = config.official_check_in
            off_out_float = config.official_check_out
            daily_hours = config.working_hours_per_day
            tolerance = config.delay_tolerance
            holidays = config.public_holiday_ids.mapped('date')
            non_working_day = int(config.non_working_day)

        # 2. Prepare Timezone
        # Use user's TZ or default to Morocco often used in this project context
        tz_name = self.env.user.tz or 'Africa/Casablanca'
        try:
            user_tz = pytz.timezone(tz_name)
        except:
            user_tz = pytz.utc

        for rec in self:
            # Init fields
            rec.normal_working_hours = 0.0
            rec.missing_hours = 0.0
            rec.overtime_hours = 0.0
            rec.holiday_hours = 0.0
            rec.delay_minutes = 0

            # ---------------------------
            # A. EXEMPTION CHECKS
            # ---------------------------
            
            # A1. Absent
            if rec.is_absent:
                # If marked absent, fully missing unless it's a holiday/weekend?
                # Usually absent means "should have worked but didn't".
                rec.missing_hours = daily_hours
                continue

            # A2. Paid Leave
            leave_domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approved'),
                ('date_from', '<=', rec.date),
                ('date_to', '>=', rec.date),
            ]
            if self.env['custom.leave'].search_count(leave_domain) > 0:
                rec.normal_working_hours = daily_hours # Count as worked
                continue

            # A3. Rest Day (e.g. Sunday)
            if rec.date.weekday() == non_working_day:
                # If they worked on Sunday, maybe count as Overtime?
                # For now, following previous logic: ignored.
                continue

            # A4. Public Holiday
            if rec.date in holidays:
                if rec.check_in and rec.check_out:
                    duration = (rec.check_out - rec.check_in).total_seconds() / 3600.0
                    rec.holiday_hours = max(0.0, duration)
                    rec.normal_working_hours = rec.holiday_hours # Counted for stats
                continue

            # ---------------------------
            # B. CALCULATION LOGIC (TZ AWARE)
            # ---------------------------
            if not rec.check_in or not rec.check_out:
                # No data entered yet
                rec.missing_hours = daily_hours
                continue

            # 1. Localize Database Times (UTC -> Local)
            # Odoo datetimes are naive UTC. We localize them to UTC, then convert to User TZ.
            c_in_utc = pytz.utc.localize(rec.check_in)
            c_out_utc = pytz.utc.localize(rec.check_out)
            
            c_in_local = c_in_utc.astimezone(user_tz)
            c_out_local = c_out_utc.astimezone(user_tz)

            # 2. Construct Official Times in Local TZ
            # We use rec.date combined with configured float hours
            def get_dt(target_date, float_hour):
                hours = int(float_hour)
                minutes = int((float_hour - hours) * 60)
                # create naive local datetime
                naive_dt = datetime.combine(target_date, time(hours, minutes))
                # localize it (assume it represents local wall clock time)
                return user_tz.localize(naive_dt)

            off_in_local = get_dt(rec.date, off_in_float)
            off_out_local = get_dt(rec.date, off_out_float)

            # 3. Calculate Delay
            # Actual In > Official In + Tolerance
            # Note: We compare localized datetimes directly
            
            # Guard: ensure we are comparing same day or handling night shift
            # Assuming day shift for now based on context
            
            if c_in_local > off_in_local:
                diff = (c_in_local - off_in_local).total_seconds() / 60.0
                if diff > tolerance:
                    rec.delay_minutes = int(diff)
            
            # 4. Calculate Worked Hours within Schedule
            # Effective In = max(Actual In, Official In)
            # Effective Out = min(Actual Out, Official Out)
            
            eff_in = max(c_in_local, off_in_local)
            eff_out = min(c_out_local, off_out_local)

            if eff_out > eff_in:
                w_sec = (eff_out - eff_in).total_seconds()
                rec.normal_working_hours = w_sec / 3600.0
            else:
                rec.normal_working_hours = 0.0

            # 5. Missing Hours
            rec.missing_hours = max(0.0, daily_hours - rec.normal_working_hours)

            # 6. Overtime
            # User wants: Strictly time AFTER Official Out
            if c_out_local > off_out_local:
                o_sec = (c_out_local - off_out_local).total_seconds()
                rec.overtime_hours = o_sec / 3600.0

    @api.model
    def create(self, vals):
        record = super(CustomAttendance, self).create(vals)
        record._handle_absence_leave_creation()
        return record

    def write(self, vals):
        res = super(CustomAttendance, self).write(vals)
        if 'is_absent' in vals or 'absence_type' in vals:
            for rec in self:
                rec._handle_absence_leave_creation()
        return res

    def _handle_absence_leave_creation(self):
        for rec in self:
            if rec.is_absent and rec.absence_type == 'leave':
                # Check if leave already exists to avoid duplicates
                existing_leave = self.env['custom.leave'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('date_from', '=', rec.date),
                    ('date_to', '=', rec.date),
                    ('leave_type', '=', 'paid')
                ])
                if not existing_leave:
                    # Check Balance
                    if rec.employee_id.leaves_remaining < 1:
                        # Allow UI but block save (Constraint-like)
                        raise exceptions.ValidationError("Pas de solde de congé restant")
                    
                    # Create Approved Leave
                    self.env['custom.leave'].create({
                        'employee_id': rec.employee_id.id,
                        'date_from': rec.date,
                        'date_to': rec.date,
                        'leave_type': 'paid',
                        'reason': 'Absence marquée depuis la fiche de présence',
                        'state': 'approved'
                    })
