from odoo import models, fields, api, exceptions
import pytz

class SuiviPresence(models.Model):
    _name = 'suivi.presence'
    _description = 'Suivi de Présence'
    _order = 'datetime desc'

    employee_id = fields.Many2one('suivi.employee', string='Employé', required=True, ondelete='cascade')
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

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._check_entry_compliance()
        
        # ----------------------------------
        # 3️⃣ Absence → Paid Leave logic
        # ----------------------------------
        if rec.type == 'absent' and rec.absence_type == 'leave':
            # ... (leave logic remains here, calling self.env...)
            rec._process_absence_leave_creation()
            
        return rec

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            rec._check_entry_compliance()
        return res

    def _check_entry_compliance(self):
        """ Block Entree > 10:00 AM for non-admins """
        if self.env.user.has_group('suivi_presence.group_suivi_admin'):
            return

        for rec in self:
            if rec.type == 'entree' and rec.datetime:
                # Odoo Datetime is UTC. Convert to Casa.
                dt = rec.datetime
                if not dt.tzinfo:
                    dt = pytz.utc.localize(dt)
                
                user_tz = pytz.timezone('Africa/Casablanca')
                local_dt = dt.astimezone(user_tz)
                
                hour_dec = local_dt.hour + local_dt.minute / 60.0
                if hour_dec > 10.0:
                     raise exceptions.ValidationError(
                        "Check-in is not allowed after 10:00 AM. Please contact an administrator."
                    )
    
    def _process_absence_leave_creation(self):
        """ Separate method for leave creation logic to keep create() clean """
        if self.type == 'absent' and self.absence_type == 'leave':
             # Check if day is holiday or non-working day
            config = self.env['suivi.presence.config'].get_main_config()
            target_date = self.datetime.date()

            is_valid_day = True
            if config:
                if target_date.weekday() == int(config.non_working_day):
                    is_valid_day = False

                if self.env['suivi.public.holiday'].search([('date', '=', target_date)], limit=1):
                    is_valid_day = False

            if is_valid_day:
                leave = self.env['suivi.leave'].create({
                    'employee_id': self.employee_id.id,
                    'date_from': target_date,
                    'date_to': target_date,
                    'leave_type': 'paid',
                    'reason': 'Absence marked from presence tracking',
                    'state': 'draft',
                })
                leave.action_approve()

