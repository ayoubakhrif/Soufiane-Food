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
        # Check-in restriction BEFORE create
        self._check_entry_compliance(vals)
        
        rec = super().create(vals)
        
        # ----------------------------------
        # 3️⃣ Absence → Paid Leave logic
        # ----------------------------------
        if rec.type == 'absent' and rec.absence_type == 'leave':
            rec._process_absence_leave_creation()
            
        return rec

    def write(self, vals):
        # Check-in restriction BEFORE write
        self._check_entry_compliance(vals)
        
        res = super().write(vals)
        return res

    def _check_entry_compliance(self, vals):
        """ 
        Block creation/modification of 'Entrée' for TODAY if Current System Time > 10:00 AM.
        Allowed: Past dates, Future dates, Admins.
        """
        if self.env.user.has_group('suivi_presence.group_suivi_admin'):
            return

        # 1. Get Current System Time in Casablanca
        user_tz = pytz.timezone('Africa/Casablanca')
        # fields.Datetime.now() is UTC. We convert to Casa.
        utc_now = fields.Datetime.now()
        casa_now = utc_now.astimezone(user_tz)
        
        # 2. Check if we are past the limit (10:00 AM)
        current_decimal = casa_now.hour + casa_now.minute / 60.0
        if current_decimal <= 10.0:
            return

        # 3. Analyze Target Records
        # If self is a recordset (write), we inspect each record merged with vals
        # If self is empty/model (create), we inspect vals only
        
        targets = []
        if self:
            for rec in self:
                targets.append({
                    'type': vals.get('type') or rec.type,
                    'datetime': vals.get('datetime') or rec.datetime
                })
        else:
            targets.append({
                'type': vals.get('type'),
                'datetime': vals.get('datetime')
            })

        for t in targets:
            if t['type'] == 'entree':
                # Determin Target Date
                dt_val = t['datetime']
                if dt_val:
                    # Convert to datetime object if string
                    target_dt = fields.Datetime.to_datetime(dt_val)
                else:
                    # Default to NOW if missing (e.g. create default)
                    target_dt = fields.Datetime.now()

                # Convert Target to Casa for Date Comparison
                # Ensure UTC aware before converting
                if not target_dt.tzinfo:
                    target_dt = pytz.utc.localize(target_dt)
                
                target_casa = target_dt.astimezone(user_tz)

                # 4. Compare Dates
                # Rule: Block if Target Date is TODAY (and we are > 10 AM)
                if target_casa.date() == casa_now.date():
                    raise exceptions.ValidationError(
                        "Il est passé 10h00. Vous ne pouvez plus créer ou modifier une entrée pour aujourd'hui."
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

