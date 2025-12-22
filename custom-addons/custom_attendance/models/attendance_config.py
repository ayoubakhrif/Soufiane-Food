from odoo import models, fields, api, exceptions

class CustomAttendanceConfig(models.Model):
    _name = 'custom.attendance.config'
    _description = 'Attendance Configuration'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char(default='Standard Configuration', readonly=True)
    active = fields.Boolean(default=True)
    
    official_check_in = fields.Float(string='Heure entrée officielle', default=9.5, help="Time format: 9.5 = 09:30", required=True)
    official_check_out = fields.Float(string='Heure de sortie officielle', default=17.5, help="Time format: 17.5 = 17:30", required=True)
    
    working_hours_per_day = fields.Float(string='Heures de travaille /heure', default=8.0, required=True)
    overtime_coefficient = fields.Float(string='Coefficient des heures supplémentaires', default=1.0, required=True)
    delay_tolerance = fields.Integer(string='Tolérance de retard (Minutes)', default=0, help="Combien de minutes à tolérer avant de compter le retard")
    
    non_working_day = fields.Selection([
        ('0', 'Lundi'), ('1', 'Mardi'), ('2', 'Mercredi'),
        ('3', 'Jeudi'), ('4', 'Vendredi'), ('5', 'Samedi'), ('6', 'Dimanche')
    ], string='Jour de repos', default='6', required=True)

    public_holiday_ids = fields.One2many(
        'custom.attendance.public.holiday', 
        'config_id', 
        string='Jours Fériés'
    )

    @api.model
    def create(self, vals):
        if self.search_count([('active', '=', True)]) >= 1 and vals.get('active', True):
            raise exceptions.ValidationError("Seulement une seule configuration est possible, pas deux.")
        return super(CustomAttendanceConfig, self).create(vals)

    @api.constrains('active')
    def _check_single_active_config(self):
        if self.search_count([('active', '=', True)]) > 1:
            raise exceptions.ValidationError("Seulement une seule configuration est possible, pas deux.")
            
    @api.model
    def get_main_config(self):
        return self.search([('active', '=', True)], limit=1)

class CustomAttendancePublicHoliday(models.Model):
    _name = 'custom.attendance.public.holiday'
    _description = 'Public Holiday'
    
    config_id = fields.Many2one('custom.attendance.config', string='Configuration', ondelete='cascade')
    name = fields.Char(string='Description', required=True)
    date = fields.Date(string='Date', required=True)
