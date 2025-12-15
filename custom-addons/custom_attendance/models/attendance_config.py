from odoo import models, fields, api, exceptions

class CustomAttendanceConfig(models.Model):
    _name = 'custom.attendance.config'
    _description = 'Attendance Configuration'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char(default='Standard Configuration', readonly=True)
    active = fields.Boolean(default=True)
    
    official_check_in = fields.Float(string='Official Check-In Time', default=9.5, help="Time format: 9.5 = 09:30", required=True)
    official_check_out = fields.Float(string='Official Check-Out Time', default=17.5, help="Time format: 17.5 = 17:30", required=True)
    
    working_hours_per_day = fields.Float(string='Working Hours / Day', default=8.0, required=True)
    overtime_coefficient = fields.Float(string='Overtime Coefficient', default=1.0, required=True)
    delay_tolerance = fields.Integer(string='Delay Tolerance (Minutes)', default=0, help="Minutes of tolerance before counting delay")
    
    non_working_day = fields.Selection([
        ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'),
        ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday')
    ], string='Non-Working Day', default='6', required=True)

    @api.model
    def create(self, vals):
        if self.search_count([('active', '=', True)]) >= 1 and vals.get('active', True):
            raise exceptions.ValidationError("Only one active configuration is allowed.")
        return super(CustomAttendanceConfig, self).create(vals)

    @api.constrains('active')
    def _check_single_active_config(self):
        if self.search_count([('active', '=', True)]) > 1:
            raise exceptions.ValidationError("Only one active configuration is allowed.")
            
    @api.model
    def get_main_config(self):
        return self.search([('active', '=', True)], limit=1)
