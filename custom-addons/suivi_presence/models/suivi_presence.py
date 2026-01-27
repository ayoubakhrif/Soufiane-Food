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
        # ----------------------------------
        # 1️⃣ Check-in restriction BEFORE create
        # ----------------------------------
        if vals.get('type') == 'entree' and not self.env.user.has_group('suivi_presence.group_suivi_admin'):
            dt = fields.Datetime.to_datetime(vals.get('datetime'))
            user_tz = pytz.timezone('Africa/Casablanca')
            local_dt = dt.astimezone(user_tz)

            hour_dec = local_dt.hour + local_dt.minute / 60.0
            if hour_dec > 10.0:
                raise exceptions.ValidationError(
                    "Check-in is not allowed after 10:00 AM. Please contact an administrator."
                )

        # ----------------------------------
        # 2️⃣ Create record safely
        # ----------------------------------
        rec = super().create(vals)

        # ----------------------------------
        # 3️⃣ Absence → Paid Leave logic
        # ----------------------------------
        if rec.type == 'absent' and rec.absence_type == 'leave':
            config = self.env['suivi.presence.config'].get_main_config()
            target_date = rec.datetime.date()

            is_valid_day = True
            if config:
                if target_date.weekday() == int(config.non_working_day):
                    is_valid_day = False

                if self.env['suivi.public.holiday'].search([('date', '=', target_date)], limit=1):
                    is_valid_day = False

            if is_valid_day:
                leave = self.env['suivi.leave'].create({
                    'employee_id': rec.employee_id.id,
                    'date_from': target_date,
                    'date_to': target_date,
                    'leave_type': 'paid',
                    'reason': 'Absence marked from presence tracking',
                    'state': 'draft',
                })
                leave.action_approve()

        return rec
