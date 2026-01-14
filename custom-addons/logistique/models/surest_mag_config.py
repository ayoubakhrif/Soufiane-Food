from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SurestMagConfig(models.Model):
    _name = 'logistique.surest_mag.config'
    _description = 'Configuration Tarifs Surest/Mag'
    _rec_name = 'shipping_id'

    shipping_id = fields.Many2one('logistique.shipping', string='Shipping Company', required=True)
    container_type = fields.Selection([
        ('generals', 'Generals'),
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
         'A configuration already exists for this combination of Shipping Company, Type, and Size!')
    ]
    
    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.shipping_id.name} - {rec.container_type} - {rec.container_size}"
            result.append((rec.id, name))
        return result

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
