from odoo import models, fields, api

class SuiviPresence(models.Model):
    _name = 'suivi.presence'
    _description = 'Suivi de Présence'
    _order = 'datetime desc'

    employee_id = fields.Many2one('suivi.employee', string='Employé', required=True, ondelete='cascade')
    
    # Related fields
    employee_phone = fields.Char(related='employee_id.phone', string='Téléphone', readonly=True)
    employee_site = fields.Selection(related='employee_id.payroll_site', string='Site de Paie', readonly=True)

    datetime = fields.Datetime(string='Date et Heure', required=True, default=fields.Datetime.now)
    type = fields.Selection([
        ('entree', 'Entrée'),
        ('sortie', 'Sortie'),
        ('absent', 'Absent')
    ], string='Type', required=True)
    
    absence_type = fields.Selection([
        ('deduction', 'Déduit du salaire'),
        ('leave', 'Consomme un jour de congé')
    ], string="Type d'absence")

    site = fields.Selection([
        ('mediouna', 'Mediouna'),
        ('casa', 'Casa')
    ], string='Site de Travail', required=True, default='mediouna')

    @api.onchange('employee_id')
    def _onchange_employee_site(self):
        if self.employee_id and self.employee_id.payroll_site:
            self.site = self.employee_id.payroll_site

    @api.model
    def create(self, vals):
        rec = super(SuiviPresence, self).create(vals)
        if rec.type == 'entree':
            # Check-in Restriction: 10:00 AM
            # Allowed for Admins (suivi_presence.group_suivi_admin)
            if not self.env.user.has_group('suivi_presence.group_suivi_admin'):
                import pytz
                user_tz = pytz.timezone('Africa/Casablanca')
                # Odoo Datetime fields are stored in UTC and are naive in Python code
                # We must localize to UTC first, then convert to target timezone
                utc_dt = pytz.utc.localize(rec.datetime)
                local_dt = utc_dt.astimezone(user_tz)
                
                # Compare decimal hour
                hour_dec = local_dt.hour + local_dt.minute / 60.0
                if hour_dec > 10.0:
                    from odoo import exceptions
                    raise exceptions.ValidationError("L'entrée n'est pas autorisée après 10:00. Contactez un administrateur.")

        if rec.type == 'absent' and rec.absence_type == 'leave':
            # Check if day is holiday or non-working day
            config = self.env['suivi.presence.config'].get_main_config()
            target_date = rec.datetime.date()
            
            is_valid_day = True
            if config:
                # Check Non Working Day
                non_working = int(config.non_working_day)
                if target_date.weekday() == non_working:
                    is_valid_day = False
                
                # Check Public Holiday
                holiday = self.env['suivi.public.holiday'].search([
                    ('date', '=', target_date)
                ], limit=1)
                if holiday:
                    is_valid_day = False
            
            if is_valid_day:
                # Create a Paid Leave in DRAFT
                leave_vals = {
                    'employee_id': rec.employee_id.id,
                    'date_from': target_date,
                    'date_to': target_date,
                    'leave_type': 'paid',
                    'reason': 'Absence marquée depuis le suivi de présence',
                    'state': 'draft'
                }
                self.env['suivi.leave'].create(leave_vals)
        return rec
