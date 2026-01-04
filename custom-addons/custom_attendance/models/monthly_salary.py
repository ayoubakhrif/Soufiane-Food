from odoo import models, fields, api, exceptions
import math
import pytz
import re
from datetime import datetime, timedelta, time


class CustomAttendance(models.Model):
    _name = 'custom.attendance'
    _description = 'Daily Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('custom.employee', string='Employés', required=True, tracking=True)

    def _auto_init(self):
        cr = self.env.cr
        cr.execute("SELECT data_type FROM information_schema.columns WHERE table_name = 'custom_attendance' AND column_name = 'check_in'")
        res = cr.fetchone()
        if res and res[0] == 'double precision':
            cr.execute("ALTER TABLE custom_attendance DROP COLUMN check_in CASCADE")
            cr.execute("ALTER TABLE custom_attendance DROP COLUMN check_out CASCADE")
            
        super()._auto_init()

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    
    check_in = fields.Datetime(string='Heure entrée', required=False)
    check_out = fields.Datetime(string='Heure de sortie', required=False)
    
    check_in_time = fields.Char(string='H.entrée', compute='_compute_times', inverse='_inverse_times', tracking=True)
    check_out_time = fields.Char(string='H.sortie', compute='_compute_times', inverse='_inverse_times', tracking=True)
    
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

    @api.depends('check_in', 'check_out', 'date')
    def _compute_times(self):
        tz_name = self.env.user.tz or 'Africa/Casablanca'
        try:
            user_tz = pytz.timezone(tz_name)
        except:
            user_tz = pytz.utc
        for rec in self:
            if rec.check_in:
                dt_local = pytz.utc.localize(rec.check_in).astimezone(user_tz)
                rec.check_in_time = dt_local.strftime('%H:%M')
            else:
                rec.check_in_time = False
            
            if rec.check_out:
                dt_local = pytz.utc.localize(rec.check_out).astimezone(user_tz)
                rec.check_out_time = dt_local.strftime('%H:%M')
            else:
                rec.check_out_time = False

    def _inverse_times(self):
        tz_name = self.env.user.tz or 'Africa/Casablanca'
        try:
            user_tz = pytz.timezone(tz_name)
        except:
            user_tz = pytz.utc
        for rec in self:
            if not rec.date:
                continue
            
            if rec.check_in_time:
                rec.check_in = self._get_utc_from_time(rec.date, rec.check_in_time, user_tz)
            
            if rec.check_out_time:
                rec.check_out = self._get_utc_from_time(rec.date, rec.check_out_time, user_tz)
            if rec.check_in_time and rec.check_out_time:
                if rec.check_out_time < rec.check_in_time:
                    raise exceptions.ValidationError("Heure de sortie invalide.")

    def _get_utc_from_time(self, date_val, time_str, user_tz):
        try:
            h, m = map(int, time_str.split(':'))
            naive_dt = datetime.combine(date_val, time(h, m))
            local_dt = user_tz.localize(naive_dt)
            return local_dt.astimezone(pytz.utc).replace(tzinfo=None)
        except:
            return False

    @api.onchange('date')
    def _onchange_date_sync_times(self):
        tz_name = self.env.user.tz or 'Africa/Casablanca'
        try:
            user_tz = pytz.timezone(tz_name)
        except:
            user_tz = pytz.utc
        if self.date:
            if self.check_in_time:
                self.check_in = self._get_utc_from_time(self.date, self.check_in_time, user_tz)
            if self.check_out_time:
                self.check_out = self._get_utc_from_time(self.date, self.check_out_time, user_tz)

    @api.constrains('check_in', 'check_out')
    def _check_validity(self):
        for rec in self:
            if rec.check_in and rec.check_out and rec.check_out < rec.check_in:
                raise exceptions.ValidationError("Heure d'entrée ne peut pas etre supérieure à l'heure de sortie.")

    @api.depends('check_in', 'check_out', 'employee_id', 'date', 'is_absent')
    def _compute_hours(self):
        """
        PROBLÈMES RÉSOLUS:
        1. Le retard n'était pas calculé correctement (condition inversée)
        2. Les heures supplémentaires ne comptaient que le soir
        3. La logique de comparaison des heures locales était incorrecte
        """
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
            # Initialisation
            rec.normal_working_hours = 0.0
            rec.missing_hours = 0.0
            rec.overtime_hours = 0.0
            rec.holiday_hours = 0.0
            rec.delay_minutes = 0

            # A. VÉRIFICATIONS D'EXEMPTION
            if rec.is_absent:
                rec.missing_hours = daily_hours
                continue

            # Congé payé approuvé
            leave_domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approved'),
                ('date_from', '<=', rec.date),
                ('date_to', '>=', rec.date),
            ]
            if self.env['custom.leave'].search_count(leave_domain) > 0:
                rec.normal_working_hours = daily_hours
                continue

            # Jour de repos
            if rec.date.weekday() == non_working_day:
                continue

            # Jour férié
            if rec.date in holidays:
                if rec.check_in and rec.check_out:
                    duration = (rec.check_out - rec.check_in).total_seconds() / 3600.0
                    rec.holiday_hours = max(0.0, duration)
                    rec.normal_working_hours = rec.holiday_hours
                continue

            # B. CALCUL AVEC DONNÉES DE PRÉSENCE
            if not rec.check_in or not rec.check_out:
                rec.missing_hours = daily_hours
                continue

            # Conversion en temps local
            c_in_utc = pytz.utc.localize(rec.check_in)
            c_out_utc = pytz.utc.localize(rec.check_out)
            
            c_in_local = c_in_utc.astimezone(user_tz)
            c_out_local = c_out_utc.astimezone(user_tz)

            # Construction des heures officielles
            def get_dt(target_date, float_hour):
                hours = int(float_hour)
                minutes = int((float_hour - hours) * 60)
                naive_dt = datetime.combine(target_date, time(hours, minutes))
                return user_tz.localize(naive_dt)

            off_in_local = get_dt(rec.date, off_in_float)
            off_out_local = get_dt(rec.date, off_out_float)

            # ====== FIX 1: CALCUL DU RETARD ======
            # Le retard se calcule quand l'employé arrive APRÈS l'heure officielle
            if c_in_local > off_in_local:
                diff_minutes = (c_in_local - off_in_local).total_seconds() / 60.0
                if diff_minutes > tolerance:
                    rec.delay_minutes = int(diff_minutes)
            else:
                rec.delay_minutes = 0

            # ====== FIX 2: HEURES NORMALES ======
            # Heures travaillées dans la plage officielle
            eff_in = max(c_in_local, off_in_local)
            eff_out = min(c_out_local, off_out_local)

            if eff_out > eff_in:
                w_sec = (eff_out - eff_in).total_seconds()
                rec.normal_working_hours = w_sec / 3600.0
            else:
                rec.normal_working_hours = 0.0

            # Heures manquantes
            rec.missing_hours = max(0.0, daily_hours - rec.normal_working_hours)

            # ====== FIX 3: HEURES SUPPLÉMENTAIRES ======
            # SEULEMENT le temps travaillé APRÈS l'heure officielle de sortie
            
            # Départ après l'heure officielle = Overtime
            if c_out_local > off_out_local:
                rec.overtime_hours = (c_out_local - off_out_local).total_seconds() / 3600.0
            else:
                rec.overtime_hours = 0.0

    @api.model
    def create(self, vals):
        rec = super(CustomAttendance, self).create(vals)
        rec._handle_absence_leave_creation()
        return rec

    def write(self, vals):
        res = super(CustomAttendance, self).write(vals)
        for rec in self:
            if 'is_absent' in vals or 'absence_type' in vals:
                rec._handle_absence_leave_creation()
        return res

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

    @api.onchange('check_in_time', 'check_out_time', 'date')
    def _onchange_recompute_hours(self):
        tz_name = 'Africa/Casablanca'
        try:
            user_tz = pytz.timezone(tz_name)
        except:
            user_tz = pytz.utc

        for rec in self:
            if rec.date and rec.check_in_time:
                rec.check_in = self._get_utc_from_time(
                    rec.date, rec.check_in_time, user_tz
                )

            if rec.date and rec.check_out_time:
                rec.check_out = self._get_utc_from_time(
                    rec.date, rec.check_out_time, user_tz
                )

            if rec.check_in and rec.check_out:
                rec._compute_hours()