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

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.payroll_site:
            self.site = self.employee_id.payroll_site

    @api.constrains('employee_id', 'type', 'datetime')
    def _check_unique_entry(self):
        for rec in self:
            if rec.type in ['entree', 'absent']:
                # Convert to date to check "Same Day"
                user_tz = pytz.timezone('Africa/Casablanca')
                # Ensure we handle naive datetimes (though stored ones are usually UTC)
                dt = rec.datetime
                if not dt.tzinfo:
                    dt = pytz.utc.localize(dt)
                    
                rec_dt = dt.astimezone(user_tz)
                start_of_day = rec_dt.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc)
                end_of_day = rec_dt.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(pytz.utc)

                domain = [
                    ('employee_id', '=', rec.employee_id.id),
                    ('type', '=', rec.type),
                    ('datetime', '>=', start_of_day),
                    ('datetime', '<=', end_of_day),
                    ('id', '!=', rec.id)
                ]
                if self.search_count(domain) > 0:
                    raise exceptions.ValidationError(f"Cet employé a déjà un enregistrement de type '{rec.type}' pour ce jour.")

    @api.onchange('employee_id', 'type', 'datetime')
    def _onchange_check_duplicate_exit(self):
        if self.type == 'sortie' and self.employee_id and self.datetime:
            try:
                user_tz = pytz.timezone('Africa/Casablanca')
                dt = self.datetime
                if not dt.tzinfo:
                    dt = pytz.utc.localize(dt)
                
                rec_dt = dt.astimezone(user_tz)
                start_of_day = rec_dt.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc)
                end_of_day = rec_dt.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(pytz.utc)
                
                domain = [
                    ('employee_id', '=', self.employee_id.id),
                    ('type', '=', 'sortie'),
                    ('datetime', '>=', start_of_day),
                    ('datetime', '<=', end_of_day),
                ]
                if self._origin.id:
                    domain.append(('id', '!=', self._origin.id))

                if self.search_count(domain) > 0:
                    return {
                        'warning': {
                            'title': "Attention",
                            'message': "Attention vous avez déjà rentré la sortie de cet employé ce jour là"
                        }
                    }
            except Exception as e:
                # Log error if needed, but don't crash
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error(f"Error in onchange check duplicate exit: {str(e)}")

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
        Strict Rules for 'Entrée' records (Creation & Modification):
        1. GLOBAL TIME LOCK: If System Time > 10:00 AM -> BLOCK EVERYTHING.
        2. DATE LOCK: Entry Date must be TODAY. Past/Future -> BLOCK.
        
        Allowed: Admins bypass all rules.
        """
        if self.env.user.has_group('suivi_presence.group_suivi_admin'):
            return

        # ---------------------------------------------------------
        # 1. SETUP: Get Current System Time in Casablanca
        # ---------------------------------------------------------
        user_tz = pytz.timezone('Africa/Casablanca')
        utc_now = fields.Datetime.now()
        casa_now = utc_now.astimezone(user_tz)
        
        # ---------------------------------------------------------
        # 2. CHECK GLOBAL TIME LOCK
        # If it is past 10:00 AM now, NO 'Entrée' operations allowed.
        # ---------------------------------------------------------
        current_decimal = casa_now.hour + casa_now.minute / 60.0
        if current_decimal > 10.0:
            # We need to see if we are dealing with an 'Entrée' record.
            # If self exists, check if any record is 'Entrée' or becoming 'Entrée'
            # If create, check vals.
            
            is_entree_operation = False
            
            # Check for Create
            if not self: 
                if vals.get('type') == 'entree':
                    is_entree_operation = True
            
            # Check for Write
            else:
                for rec in self:
                    new_type = vals.get('type') or rec.type
                    if new_type == 'entree':
                        is_entree_operation = True
                        break
            
            if is_entree_operation:
                raise exceptions.ValidationError(
                    "SYSTEM LOCK: It is past 10:00 AM. No Entry operations allowed."
                )

        # ---------------------------------------------------------
        # 3. PREPARE TARGETS (For Date Check)
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 4. CHECK DATE LOCK
        # Entry Date must be TODAY.
        # ---------------------------------------------------------
        for t in targets:
            if t['type'] == 'entree':
                dt_val = t['datetime']
                if dt_val:
                    target_dt = fields.Datetime.to_datetime(dt_val)
                else:
                    target_dt = fields.Datetime.now()

                if not target_dt.tzinfo:
                    target_dt = pytz.utc.localize(target_dt)
                
                target_casa = target_dt.astimezone(user_tz)

                if target_casa.date() != casa_now.date():
                    raise exceptions.ValidationError(
                        "INVALID DATE: Entry records must be for TODAY only."
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

