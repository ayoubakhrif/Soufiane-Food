from odoo import models, fields, api, exceptions
import math
from datetime import datetime, timedelta, time


class CustomAttendance(models.Model):
    _name = 'custom.attendance'
    _description = 'Daily Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('custom.employee', string='Employés', required=True, tracking=True)
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
        config = self.env['custom.attendance.config'].get_main_config()
        if not config:
            # Fallback defaults if no config exists
            off_in_float = 9.5
            off_out_float = 17.5
            daily_hours = 8.0
            tolerance = 0
            holidays = []
            non_working_day = 6 # Default Sunday
        else:
            off_in_float = config.official_check_in
            off_out_float = config.official_check_out
            daily_hours = config.working_hours_per_day
            tolerance = config.delay_tolerance
            holidays = config.public_holiday_ids.mapped('date')
            non_working_day = int(config.non_working_day)

        for rec in self:
            # 0. Check for Absent
            if rec.is_absent:
                rec.normal_working_hours = 0.0
                rec.missing_hours = daily_hours
                rec.overtime_hours = 0.0
                rec.holiday_hours = 0.0
                rec.delay_minutes = 0
                continue

            # 0.5 Check for Paid Leave
            leave_domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approved'),
                ('date_from', '<=', rec.date),
                ('date_to', '>=', rec.date),
            ]
            
            is_on_leave = self.env['custom.leave'].search_count(leave_domain) > 0
            
            if is_on_leave:
                # Leave Logic: Treat as fully worked day
                rec.normal_working_hours = daily_hours
                rec.missing_hours = 0.0
                rec.overtime_hours = 0.0
                rec.holiday_hours = 0.0
                rec.delay_minutes = 0
                continue
                
            # Helper to convert float time to datetime on the current record date
            def float_to_dt(float_time):
                hours = int(float_time)
                minutes = int((float_time - hours) * 60)
                return datetime.combine(rec.date, time(hours, minutes))

            # 1. Check if Public Holiday OR Non-Working Day (e.g. Sunday)
            # If Sunday/Rest Day -> Ignore hours completely (Not counted as Work, Not counted as Missing)
            if rec.date.weekday() == non_working_day:
                 rec.normal_working_hours = 0.0
                 rec.missing_hours = 0.0
                 rec.overtime_hours = 0.0
                 rec.holiday_hours = 0.0
                 rec.delay_minutes = 0
            
            # If Public Holiday (and NOT rest day, handled above)
            elif rec.date in holidays:
                # Holiday Logic -> Count duration as specific Holiday Hours
                duration = (rec.check_out - rec.check_in).total_seconds() / 3600.0
                rec.holiday_hours = max(0.0, duration)
                rec.normal_working_hours = rec.holiday_hours # Count as normal too for stats (Requested behavior?)
                rec.missing_hours = 0.0 # No penalty
                rec.overtime_hours = 0.0 # Double pay replaces overtime
                rec.delay_minutes = 0

            else:
                # Normal Day Logic
                rec.holiday_hours = 0.0
                
                # Construct Official Datetimes
                try:
                    off_in_dt = float_to_dt(off_in_float)
                    off_out_dt = float_to_dt(off_out_float)
                except:
                    # Fallback if conversion fails
                    off_in_dt = rec.check_in
                    off_out_dt = rec.check_out

                # Delay Calculation
                # Late Arrival: check_in > off_in
                if rec.check_in > off_in_dt:
                    diff_seconds = (rec.check_in - off_in_dt).total_seconds()
                    delay_min = int(diff_seconds / 60)
                    rec.delay_minutes = delay_min if delay_min > tolerance else 0
                else:
                    rec.delay_minutes = 0
    
                # Core Logic: Hours within [Official_In, Official_Out]
                # Effective In: max of Actual In vs Official In
                eff_in = max(rec.check_in, off_in_dt)
                # Effective Out (for normal hours): min of Actual Out vs Official Out
                eff_out = min(rec.check_out, off_out_dt)
                
                # Normal Worked duration
                if eff_out > eff_in:
                    worked_seconds = (eff_out - eff_in).total_seconds()
                    worked_hours = worked_seconds / 3600.0
                else:
                    worked_hours = 0.0
                
                rec.normal_working_hours = min(worked_hours, daily_hours)
                
                # Missing Hours: Daily Target - Normal Worked
                rec.missing_hours = max(0.0, daily_hours - rec.normal_working_hours)
                
                # Overtime: Strictly time after Official Out
                if rec.check_out > off_out_dt:
                    over_seconds = (rec.check_out - off_out_dt).total_seconds()
                    rec.overtime_hours = over_seconds / 3600.0
                else:
                    rec.overtime_hours = 0.0

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
