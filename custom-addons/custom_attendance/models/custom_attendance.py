from odoo import models, fields, api, exceptions
import math

class CustomAttendance(models.Model):
    _name = 'custom.attendance'
    _description = 'Daily Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('custom.employee', string='Employés', required=True, tracking=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    
    check_in = fields.Float(string='Heure entrée', required=True, help="Format: 9.5 for 09:30")
    check_out = fields.Float(string='Heure de sortie', required=True, help="Format: 17.5 for 17:30")
    
    delay_minutes = fields.Integer(string='Delay (Minutes)', compute='_compute_hours', store=True)
    missing_hours = fields.Float(string='Heures manquantes', compute='_compute_hours', store=True)
    overtime_hours = fields.Float(string='Heures supplémentaires', compute='_compute_hours', store=True)
    normal_working_hours = fields.Float(string='Heures normales', compute='_compute_hours', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('locked', 'Locked')
    ], default='draft', string='Status', tracking=True)

    _sql_constraints = [
        ('unique_employee_date', 'unique(employee_id, date)', 'Chaque employé soit avoire une seule fiche de présence par jour!')
    ]

    @api.constrains('check_in', 'check_out')
    def _check_validity(self):
        for rec in self:
            if rec.check_out < rec.check_in:
                raise exceptions.ValidationError("Heure d'entrée ne peut pas etre supérieure à l'heure de sortie.")

    @api.depends('check_in', 'check_out', 'employee_id')
    def _compute_hours(self):
        config = self.env['custom.attendance.config'].get_main_config()
        if not config:
            # Fallback defaults if no config exists
            off_in = 9.5
            off_out = 17.5
            daily_hours = 8.0
            tolerance = 0
        else:
            off_in = config.official_check_in
            off_out = config.official_check_out
            daily_hours = config.working_hours_per_day
            tolerance = config.delay_tolerance

        for rec in self:
            # Delay Calculation
            if rec.check_in > off_in:
                delay_min = int((rec.check_in - off_in) * 60)
                rec.delay_minutes = delay_min if delay_min > tolerance else 0
            else:
                rec.delay_minutes = 0

            # Core Logic: Hours within [Official_In, Official_Out]
            # Effective In: max of Actual In vs Official In
            eff_in = max(rec.check_in, off_in)
            # Effective Out (for normal hours): min of Actual Out vs Official Out
            eff_out = min(rec.check_out, off_out)
            
            # Normal Worked duration
            if eff_out > eff_in:
                worked = eff_out - eff_in
            else:
                worked = 0.0
            
            rec.normal_working_hours = min(worked, daily_hours)
            
            # Missing Hours: Daily Target - Normal Worked
            # Note: This accounts for Late Arrival AND Early Departure
            rec.missing_hours = max(0.0, daily_hours - rec.normal_working_hours)
            
            # Overtime: Strictly time after Official Out
            if rec.check_out > off_out:
                rec.overtime_hours = rec.check_out - off_out
            else:
                rec.overtime_hours = 0.0
