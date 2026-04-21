from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SurestMagConfig(models.Model):
    _name = 'logistique.surest_mag.config'
    _description = 'Configuration Tarifs Surest/Mag'
    _rec_name = 'shipping_id'

    shipping_id = fields.Many2one('logistique.shipping', string='Shipping Company', required=True)
    container_type = fields.Selection([
        ('generals', 'Dry'),
        ('reefers', 'Reefers'),
    ], string='Container Type', required=True, default='generals')
    container_size = fields.Selection([
        ('20', "20'"),
        ('40', "40'"),
    ], string='Container Size', required=True, default='20')
    
    active = fields.Boolean(default=True)
    phase_ids = fields.One2many('logistique.surest_mag.phase', 'config_id', string='Phases')

    _sql_constraints = [
        ('uniq_config', 'unique(shipping_id, container_type, container_size)', 
         'Une configuration existe déjà pour cette combinaison de Shipping Company, Type, et Size!')
    ]
    
    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.shipping_id.name} - {rec.container_type} - {rec.container_size}"
            result.append((rec.id, name))
        return result

    def calculate_amounts(self, days_magasinage, days_surestarie, free_surestarie_days, container_count=1):
        self.ensure_one()
        lines = []
        total_surestarie_ht = 0.0
        total_magasinage_ht = 0.0

        if not days_magasinage and not days_surestarie:
            return {'surestarie_ht': 0.0, 'magasinage_ht': 0.0, 'lines': lines}

        current_day_index = 1
        phases = self.phase_ids.sorted(key=lambda p: p.sequence)
        free_until_day = free_surestarie_days

        for phase in phases:
            phase_start = current_day_index
            phase_end = float('inf') if phase.is_beyond else phase_start + phase.days - 1

            mag_overlap_start = max(phase_start, 1)
            mag_overlap_end = min(phase_end, days_magasinage)
            days_mag_spent_in_phase = (mag_overlap_end - mag_overlap_start + 1) if mag_overlap_end >= mag_overlap_start else 0

            sur_overlap_start = max(phase_start, free_until_day + 1)
            sur_overlap_end = min(phase_end, days_surestarie)
            days_sur_billed_in_phase = (sur_overlap_end - sur_overlap_start + 1) if sur_overlap_end >= sur_overlap_start else 0

            if days_mag_spent_in_phase > 0 or days_sur_billed_in_phase > 0:
                cnt = container_count or 1
                surest_sub = days_sur_billed_in_phase * phase.surestarie_rate * cnt
                mag_sub = days_mag_spent_in_phase * phase.magasinage_rate * cnt
                
                total_surestarie_ht += surest_sub
                total_magasinage_ht += mag_sub

                line_vals = {
                    'phase_name': f"Beyond (Rate: {phase.surestarie_rate}/{phase.magasinage_rate})" if phase.is_beyond else f"Phase {phase.sequence} ({phase.days} days)",
                    'days_magasinage': days_mag_spent_in_phase,
                    'days_surestarie_billed': days_sur_billed_in_phase,
                    'surestarie_rate': phase.surestarie_rate,
                    'magasinage_rate': phase.magasinage_rate,
                    'surestarie_subtotal': surest_sub,
                    'magasinage_subtotal': mag_sub,
                }
                lines.append(line_vals)

            if phase.is_beyond:
                break
            else:
                current_day_index += phase.days

        return {
            'surestarie_ht': total_surestarie_ht,
            'magasinage_ht': total_magasinage_ht,
            'lines': lines
        }

class SurestMagPhase(models.Model):
    _name = 'logistique.surest_mag.phase'
    _description = 'Phase Tarifaire Surest/Mag'
    _order = 'sequence, id'

    config_id = fields.Many2one('logistique.surest_mag.config', string='Configuration', ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    
    days = fields.Integer(string='Days', help="Number of days in this phase")
    surestarie_rate = fields.Float(string='Surestarie Rate (MAD/Day)')
    magasinage_rate = fields.Float(string='Magasinage Rate (MAD/Day)')
    
    is_beyond = fields.Boolean(string='Is Beyond', default=False, 
                               help="Check this if this phase applies to all remaining days beyond the previous phases.")

    @api.constrains('days', 'is_beyond')
    def _check_days(self):
        for rec in self:
            if not rec.is_beyond and rec.days <= 0:
                raise ValidationError("Days must be greater than 0 for normal phases.")
            if rec.is_beyond and rec.days != 0:
                 # Optional: force days to 0 if beyond, or just ignore it. 
                 # Let's clean it up on write/create to be safe, but validation is ok too.
                 pass
