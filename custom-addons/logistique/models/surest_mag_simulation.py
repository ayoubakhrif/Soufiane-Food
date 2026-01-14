from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

class SurestMagSimulation(models.Model):
    _name = 'logistique.surest_mag.simulation'
    _description = 'Simulation Surest/Mag'
    _rec_name = 'id'

    shipping_id = fields.Many2one('logistique.shipping', string='Shipping Company', required=True)
    container_type = fields.Selection([
        ('generals', 'Generals'),
        ('reefers', 'Reefers'),
    ], string='Container Type', required=True, default='generals')
    container_size = fields.Selection([
        ('20', "20'"),
        ('40', "40'"),
    ], string='Container Size', required=True, default='20')
    
    entry_date = fields.Date(string='Entry Date', required=True, default=fields.Date.context_today)
    exit_date = fields.Date(string='Exit Date', required=True, default=fields.Date.context_today)
    
    total_days = fields.Integer(string='Total Days', compute='_compute_days', store=True)
    
    config_id = fields.Many2one('logistique.surest_mag.config', string='Configuration Used', readonly=True)
    
    line_ids = fields.One2many('logistique.surest_mag.simulation.line', 'simulation_id', string='Breakdown')
    
    total_surestarie = fields.Float(string='Total Surestarie', compute='_compute_totals', store=True)
    total_magasinage = fields.Float(string='Total Magasinage', compute='_compute_totals', store=True)
    grand_total = fields.Float(string='Grand Total', compute='_compute_totals', store=True)

    @api.depends('entry_date', 'exit_date')
    def _compute_days(self):
        for rec in self:
            if rec.entry_date and rec.exit_date:
                if rec.exit_date < rec.entry_date:
                    rec.total_days = 0 
                else:
                    rec.total_days = (rec.exit_date - rec.entry_date).days + 1
            else:
                rec.total_days = 0

    @api.constrains('entry_date', 'exit_date')
    def _check_dates(self):
        for rec in self:
            if rec.entry_date and rec.exit_date and rec.exit_date < rec.entry_date:
                raise ValidationError("Exit Date cannot be before Entry Date.")

    @api.onchange('shipping_id', 'container_type', 'container_size', 'entry_date', 'exit_date')
    def _onchange_simulation_params(self):
        if self.shipping_id and self.container_type and self.container_size and self.entry_date and self.exit_date:
            self.action_simulate()

    def action_simulate(self):
        self.ensure_one()
        
        # 1. Find Configuration
        config = self.env['logistique.surest_mag.config'].search([
            ('shipping_id', '=', self.shipping_id.id),
            ('container_type', '=', self.container_type),
            ('container_size', '=', self.container_size),
        ], limit=1)
        
        if not config:
            # We can raise a warning or just clear result. 
            # Raising warning in onchange is disruptive, so maybe just set a flag or message.
            # But for button click / model save, we need to know.
            # For now, if called from onchange, we just clear lines if no config found.
            self.config_id = False
            self.line_ids = [(5, 0, 0)]
            self.total_surestarie = 0
            self.total_magasinage = 0
            self.grand_total = 0
            return

        self.config_id = config
        
        # 2. Calculate
        total_days = (self.exit_date - self.entry_date).days + 1
        if total_days <= 0:
            return

        lines = []
        days_remaining = total_days
        
        # Sort phases by sequence
        phases = config.phase_ids.sorted(key=lambda p: p.sequence)
        
        for phase in phases:
            if days_remaining <= 0:
                break
                
            days_in_phase = 0
            
            if phase.is_beyond:
                # Consume all remaining days
                days_in_phase = days_remaining
            else:
                # Consume up to phase.days or remaining
                days_in_phase = min(days_remaining, phase.days)
            
            if days_in_phase > 0:
                surest_sub = days_in_phase * phase.surestarie_rate
                mag_sub = days_in_phase * phase.magasinage_rate
                
                line_vals = {
                    'phase_name': f"Beyond (Rate: {phase.surestarie_rate}/{phase.magasinage_rate})" if phase.is_beyond else f"Phase {phase.sequence} ({phase.days} days)",
                    'days_spent': days_in_phase,
                    'surestarie_rate': phase.surestarie_rate,
                    'magasinage_rate': phase.magasinage_rate,
                    'surestarie_subtotal': surest_sub,
                    'magasinage_subtotal': mag_sub,
                }
                lines.append((0, 0, line_vals))
                
                days_remaining -= days_in_phase

        self.line_ids = [(5, 0, 0)] + lines
        # Trigger compute of totals

    @api.depends('line_ids.surestarie_subtotal', 'line_ids.magasinage_subtotal')
    def _compute_totals(self):
        for rec in self:
            rec.total_surestarie = sum(l.surestarie_subtotal for l in rec.line_ids)
            rec.total_magasinage = sum(l.magasinage_subtotal for l in rec.line_ids)
            rec.grand_total = rec.total_surestarie + rec.total_magasinage


class SurestMagSimulationLine(models.Model):
    _name = 'logistique.surest_mag.simulation.line'
    _description = 'Ligne de Simulation Surest/Mag'

    simulation_id = fields.Many2one('logistique.surest_mag.simulation', string='Simulation', ondelete='cascade')
    
    phase_name = fields.Char(string='Phase')
    days_spent = fields.Integer(string='Days Allocated')
    surestarie_rate = fields.Float(string='Surest. Rate')
    magasinage_rate = fields.Float(string='Mag. Rate')
    
    surestarie_subtotal = fields.Float(string='Surest. Total')
    magasinage_subtotal = fields.Float(string='Mag. Total')
