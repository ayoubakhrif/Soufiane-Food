from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

class SurestMagSimulation(models.Model):
    _name = 'logistique.surest_mag.simulation'
    _description = 'Simulation Surest/Mag'
    _rec_name = 'id'

    shipping_id = fields.Many2one('logistique.shipping', string='Shipping Company', required=True)
    container_type = fields.Selection([
        ('generals', 'Dry'),
        ('reefers', 'Reefers'),
    ], string='Container Type', required=True, default='generals')
    container_size = fields.Selection([
        ('20', "20'"),
        ('40', "40'"),
    ], string='Container Size', required=True, default='20')
    
    entry_date = fields.Date(string='ETA', required=True, default=fields.Date.context_today)
    exit_date = fields.Date(string='Sortie Plein', required=True, default=fields.Date.context_today)
    returning_date = fields.Date(string='Entrée vide', required=True, default=fields.Date.context_today)
    
    total_days = fields.Integer(string='Total Days', compute='_compute_days', store=True) # Deprecated conceptual field, we use separate counts now
    
    # New Logic Fields
    free_surestarie_days = fields.Integer(string='Jours Franchise Surestarie', default=0)
    container_count = fields.Integer(string='Nombre de Conteneurs', default=1)
    
    days_magasinage = fields.Integer(string='Jours Magasinage', compute='_compute_days', store=True)
    days_surestarie = fields.Integer(string='Jours Surestarie', compute='_compute_days', store=True)

    config_id = fields.Many2one('logistique.surest_mag.config', string='Configuration Used', readonly=True)
    
    line_ids = fields.One2many('logistique.surest_mag.simulation.line', 'simulation_id', string='Breakdown')
    
    # Totals (HT, VAT, TTC)
    # Surestarie
    total_surestarie_ht = fields.Float(string='Surestarie HT', compute='_compute_totals', store=True)
    total_surestarie_vat = fields.Float(string='Surestarie TVA', compute='_compute_totals', store=True)
    total_surestarie_ttc = fields.Float(string='Surestarie TTC', compute='_compute_totals', store=True)

    # Magasinage
    total_magasinage_ht = fields.Float(string='Magasinage HT', compute='_compute_totals', store=True)
    total_magasinage_vat = fields.Float(string='Magasinage TVA', compute='_compute_totals', store=True)
    total_magasinage_ttc = fields.Float(string='Magasinage TTC', compute='_compute_totals', store=True)

    # Grand Total
    grand_total_ht = fields.Float(string='Total Général HT', compute='_compute_totals', store=True)
    grand_total_vat = fields.Float(string='Total Général TVA', compute='_compute_totals', store=True)
    grand_total_ttc = fields.Float(string='Total Général TTC', compute='_compute_totals', store=True)

    # Deprecated fields for backward compatibility (View Crash Fix)
    total_surestarie = fields.Float(string='Total Surestarie', compute='_compute_deprecated_totals')
    total_magasinage = fields.Float(string='Total Magasinage', compute='_compute_deprecated_totals')
    grand_total = fields.Float(string='Grand Total', compute='_compute_deprecated_totals')

    @api.depends('total_surestarie_ttc', 'total_magasinage_ttc', 'grand_total_ttc')
    def _compute_deprecated_totals(self):
         for rec in self:
             rec.total_surestarie = rec.total_surestarie_ttc
             rec.total_magasinage = rec.total_magasinage_ttc
             rec.grand_total = rec.grand_total_ttc

    @api.depends('entry_date', 'exit_date', 'returning_date')
    def _compute_days(self):
        for rec in self:
            rec.total_days = 0 # Deprecated
            
            # Magasinage: Entry to Exit
            if rec.entry_date and rec.exit_date and rec.exit_date >= rec.entry_date:
                rec.days_magasinage = (rec.exit_date - rec.entry_date).days + 1
            else:
                rec.days_magasinage = 0
                
            # Surestarie: Entry to Returning
            if rec.entry_date and rec.returning_date and rec.returning_date >= rec.entry_date:
                rec.days_surestarie = (rec.returning_date - rec.entry_date).days + 1
            else:
                 rec.days_surestarie = 0

    @api.constrains('entry_date', 'exit_date', 'returning_date')
    def _check_dates(self):
        for rec in self:
            if rec.entry_date:
                if rec.exit_date and rec.exit_date < rec.entry_date:
                    raise ValidationError("Date de sortie plein doit être postérieure ou égale à la date d'entrée (ETA).")
                if rec.returning_date and rec.returning_date < rec.entry_date:
                    raise ValidationError("Date retour vide doit être postérieure ou égale à la date d'entrée (ETA).")
            
            # Warning for logical flow (Returning normally after Exit)
            # Odoo doesn't support non-blocking warnings in constrains easily, 
            # usually we do this in onchange or just allow it. 
            # Given the requirement "Ideally enforce", we stick to strict check or let it slide?
            # "In case of error just show a warning" -> usually implies onchange warning.
            
    @api.onchange('entry_date', 'exit_date', 'returning_date')
    def _onchange_check_dates(self):
        if self.returning_date and self.exit_date and self.returning_date < self.exit_date:
            return {
                'warning': {
                    'title': "Avertissement de date",
                    'message': "La date de retour vide est généralement postérieure à la date de sortie plein."
                }
            }
            
    @api.onchange('shipping_id', 'container_type', 'container_size', 'entry_date', 'exit_date', 'returning_date', 'free_surestarie_days', 'container_count')
    def _onchange_simulation_params(self):
        if self.shipping_id and self.container_type and self.container_size and self.entry_date:
             # Trigger simulate if dates are sensical
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
            self.config_id = False
            self.line_ids = [(5, 0, 0)]
            self._reset_totals()
            return

        self.config_id = config
        
        # Date Logic validation
        if not self.days_magasinage and not self.days_surestarie:
             self._reset_totals()
             self.line_ids = [(5, 0, 0)]
             return

        result = config.calculate_amounts(self.days_magasinage, self.days_surestarie, self.free_surestarie_days, self.container_count)
        
        lines = [(0, 0, line_vals) for line_vals in result['lines']]
        self.line_ids = [(5, 0, 0)] + lines
        # Totals are computed by _compute_totals triggers

    def _reset_totals(self):
        self.total_surestarie_ht = 0
        self.total_surestarie_vat = 0
        self.total_surestarie_ttc = 0
        self.total_magasinage_ht = 0
        self.total_magasinage_vat = 0
        self.total_magasinage_ttc = 0
        self.grand_total_ht = 0
        self.grand_total_vat = 0
        self.grand_total_ttc = 0

    @api.depends('line_ids.surestarie_subtotal', 'line_ids.magasinage_subtotal')
    def _compute_totals(self):
        for rec in self:
            # HT
            rec.total_surestarie_ht = sum(l.surestarie_subtotal for l in rec.line_ids)
            rec.total_magasinage_ht = sum(l.magasinage_subtotal for l in rec.line_ids)
            rec.grand_total_ht = rec.total_surestarie_ht + rec.total_magasinage_ht
            
            # VAT (20%)
            rec.total_surestarie_vat = rec.total_surestarie_ht * 0.20
            rec.total_magasinage_vat = rec.total_magasinage_ht * 0.20
            rec.grand_total_vat = rec.grand_total_ht * 0.20
            
            # TTC
            rec.total_surestarie_ttc = rec.total_surestarie_ht + rec.total_surestarie_vat
            rec.total_magasinage_ttc = rec.total_magasinage_ht + rec.total_magasinage_vat
            rec.grand_total_ttc = rec.grand_total_ht + rec.grand_total_vat

class SurestMagSimulationLine(models.Model):
    _name = 'logistique.surest_mag.simulation.line'
    _description = 'Ligne de Simulation Surest/Mag'

    simulation_id = fields.Many2one('logistique.surest_mag.simulation', string='Simulation', ondelete='cascade')
    
    phase_name = fields.Char(string='Phase')
    
    days_magasinage = fields.Integer(string='Jours Mag.')
    days_surestarie_billed = fields.Integer(string='Jours Sur. (Facturés)')
    
    surestarie_rate = fields.Float(string='Taux Sur.')
    magasinage_rate = fields.Float(string='Taux Mag.')
    
    surestarie_subtotal = fields.Float(string='Total Sur. HT')
    magasinage_subtotal = fields.Float(string='Total Mag. HT')
