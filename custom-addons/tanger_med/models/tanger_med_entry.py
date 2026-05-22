from odoo import models, fields, api


class TangerMedEntry(models.Model):
    _inherit = 'logistique.entry'

    sur_mag_amount = fields.Float(string='SUR+MAG', compute='_compute_surest_mag', store=True)
    sur_mag_date = fields.Date(string='SUR+MAG Date', compute='_compute_surest_mag', store=True)
    sur_mag_user = fields.Many2one(
        'res.users',
        string='SUR+MAG Saisi par',
        readonly=True,
    )

    tanger_med_lot = fields.Char(string='Lot Tanger Med')
    tanger_med_dum = fields.Char(string='DUM Tanger Med')
    destination_id = fields.Many2one('tanger.med.destination', string='Destination')
    arrival_picture = fields.Binary(string='Picture of Container')

    entry_date = fields.Date(string='Date of entry', tracking=True)
    exit_date = fields.Date(string='Date of exit', tracking=True)

    container_type = fields.Selection([
        ('generals', 'Dry'),
        ('reefers', 'Reefers'),
    ], string='Container Type')
    container_size = fields.Selection([
        ('20', "20'"),
        ('40', "40'"),
    ], string='Container Size')

    calculated_surestarie_ht = fields.Float(string='Surestarie HT (Simulé)', compute='_compute_surest_mag', store=True)
    calculated_magasinage_ht = fields.Float(string='Magasinage HT (Simulé)', compute='_compute_surest_mag', store=True)

    @api.depends('entry_date', 'exit_date', 'date_sortie_port', 'container_type', 'container_size', 'eta', 'bad_date', 'shipping_id', 'free_time', 'container_count')
    def _compute_surest_mag(self):
        for rec in self:
            rec.calculated_surestarie_ht = 0.0
            rec.calculated_magasinage_ht = 0.0
            rec.sur_mag_amount = 0.0
            rec.sur_mag_date = False
            
            start_date = rec.eta or rec.bad_date
            if not rec.shipping_id or not rec.container_type or not rec.container_size or not start_date:
                continue

            config = self.env['logistique.surest_mag.config'].search([
                ('shipping_id', '=', rec.shipping_id.id),
                ('container_type', '=', rec.container_type),
                ('container_size', '=', rec.container_size),
            ], limit=1)

            if not config:
                continue

            eff_exit_date = rec.exit_date or rec.date_sortie_port
            
            days_magasinage = 0
            if start_date and eff_exit_date and eff_exit_date >= start_date:
                days_magasinage = (eff_exit_date - start_date).days + 1
            
            days_surestarie = 0
            if start_date and rec.entry_date and rec.entry_date >= start_date:
                days_surestarie = (rec.entry_date - start_date).days + 1

            result = config.calculate_amounts(days_magasinage, days_surestarie, rec.free_time or 0, rec.container_count or 1)
            
            rec.calculated_surestarie_ht = result.get('surestarie_ht', 0.0)
            rec.calculated_magasinage_ht = result.get('magasinage_ht', 0.0)
            rec.sur_mag_amount = rec.calculated_surestarie_ht + rec.calculated_magasinage_ht
            rec.sur_mag_date = fields.Date.context_today(self)

    @api.onchange('shipping_id', 'container_type', 'container_size')
    def _onchange_check_config(self):
        if self.shipping_id and self.container_type and self.container_size:
            config = self.env['logistique.surest_mag.config'].search([
                ('shipping_id', '=', self.shipping_id.id),
                ('container_type', '=', self.container_type),
                ('container_size', '=', self.container_size),
            ], limit=1)
            if not config:
                container_type_label = dict(self._fields['container_type'].selection).get(self.container_type)
                return {
                    'warning': {
                        'title': 'Configuration Introuvable',
                        'message': f"Aucune configuration Surestarie/Magasinage trouvée pour {self.shipping_id.name} avec le type {container_type_label} et taille {self.container_size}'."
                    }
                }

    
    @api.onchange('tanger_med_lot')
    def _onchange_tanger_med_lot(self):
        if self.tanger_med_lot and self.lot and self.tanger_med_lot != self.lot:
            return {
                'warning': {
                    'title': 'Lot Incohérent',
                    'message': f"Le Lot saisi ({self.tanger_med_lot}) est différent du Lot d'Achat ({self.lot})."
                }
            }

    @api.onchange('tanger_med_dum')
    def _onchange_tanger_med_dum(self):
        # We need to fetch the DUM from the douane entry/logistique entry based on the model inheritance
        if self.tanger_med_dum and hasattr(self, 'dum') and self.dum and self.tanger_med_dum != self.dum:
            return {
                'warning': {
                    'title': 'DUM Incohérent',
                    'message': f"La DUM saisie ({self.tanger_med_dum}) est différente de la DUM Douane ({self.dum})."
                }
            }


    def write(self, vals):
        if 'exit_date' in vals and vals.get('exit_date'):
            vals['sur_mag_user'] = self.env.user.id
        return super().write(vals)
