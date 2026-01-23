from odoo import models, fields, api, exceptions

class SuiviConfig(models.Model):
    _name = 'suivi.presence.config'
    _description = 'Configuration Suivi Présence'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char(default='Standard Configuration', readonly=True)
    active = fields.Boolean(default=True)
    
    annual_leave_quota = fields.Integer(string='Quota Congé Annuel', required=True, default=18, help="Jours par an")
    working_hours_per_day = fields.Float(string='Heures de travaille / jour', default=8.0, required=True)
    overtime_coefficient = fields.Float(string='Coefficient HS', default=1.0, required=True)
    
    non_working_day = fields.Selection([
        ('0', 'Lundi'), ('1', 'Mardi'), ('2', 'Mercredi'),
        ('3', 'Jeudi'), ('4', 'Vendredi'), ('5', 'Samedi'), ('6', 'Dimanche')
    ], string='Jour de repos', default='6', required=True)

    public_holiday_ids = fields.One2many('suivi.public.holiday', 'config_id', string='Jours Fériés')

    @api.model
    def create(self, vals):
        if self.search_count([('active', '=', True)]) >= 1 and vals.get('active', True):
            raise exceptions.ValidationError("Une seule configuration active est autorisée.")
        return super(SuiviConfig, self).create(vals)

    @api.model
    def get_main_config(self):
        return self.search([('active', '=', True)], limit=1)

class SuiviPublicHoliday(models.Model):
    _name = 'suivi.public.holiday'
    _description = 'Jour Férié'
    
    config_id = fields.Many2one('suivi.presence.config', string='Configuration', ondelete='cascade')
    name = fields.Char(string='Description', required=True)
    date = fields.Date(string='Date', required=True)
