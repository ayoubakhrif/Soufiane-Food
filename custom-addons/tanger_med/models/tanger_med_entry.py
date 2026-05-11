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

    @api.depends('entry_date', 'exit_date', 'container_type', 'container_size', 'eta', 'shipping_id', 'free_time', 'container_count')
    def _compute_surest_mag(self):
        for rec in self:
            rec.calculated_surestarie_ht = 0.0
            rec.calculated_magasinage_ht = 0.0
            rec.sur_mag_amount = 0.0
            rec.sur_mag_date = False
            if not rec.shipping_id or not rec.container_type or not rec.container_size or not rec.eta:
                continue

            config = self.env['logistique.surest_mag.config'].search([
                ('shipping_id', '=', rec.shipping_id.id),
                ('container_type', '=', rec.container_type),
                ('container_size', '=', rec.container_size),
            ], limit=1)

            if not config:
                continue

            days_magasinage = 0
            if rec.eta and rec.exit_date and rec.exit_date >= rec.eta:
                days_magasinage = (rec.exit_date - rec.eta).days + 1
            
            days_surestarie = 0
            if rec.eta and rec.entry_date and rec.entry_date >= rec.eta:
                days_surestarie = (rec.entry_date - rec.eta).days + 1

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

    tanger_med_state = fields.Selection([
        ('port', 'Au Port'),
        ('sortie_port', 'Sortie de Port'),
        ('arrive_stock', 'Arrivé au Stock'),
    ], string='Statut Tanger Med', default='port', tracking=True)

    is_analyse = fields.Boolean(string='Analyse', default=False, tracking=True)
    date_analyse = fields.Date(string="Date d'Analyse", tracking=True)

    is_visite = fields.Boolean(string='Visite', default=False, tracking=True)
    date_visite = fields.Date(string="Date de Visite", tracking=True)

    date_sortie_port = fields.Date(string="Date de Sortie de Port", tracking=True)
    date_arrive_stock = fields.Date(string="Date d'Arrivée au Stock", tracking=True)

    @api.onchange('is_analyse')
    def _onchange_is_analyse(self):
        if self.is_analyse and not self.date_analyse:
            self.date_analyse = fields.Date.context_today(self)
        elif not self.is_analyse:
            self.date_analyse = False

    @api.onchange('is_visite')
    def _onchange_is_visite(self):
        if self.is_visite and not self.date_visite:
            self.date_visite = fields.Date.context_today(self)
        elif not self.is_visite:
            self.date_visite = False

    @api.onchange('date_analyse')
    def _onchange_date_analyse(self):
        self.is_analyse = bool(self.date_analyse)

    @api.onchange('date_visite')
    def _onchange_date_visite(self):
        self.is_visite = bool(self.date_visite)

    @api.onchange('date_sortie_port')
    def _onchange_date_sortie_port(self):
        if self.date_sortie_port:
            self.tanger_med_state = 'sortie_port'

    @api.onchange('date_arrive_stock')
    def _onchange_date_arrive_stock(self):
        if self.date_arrive_stock:
            self.tanger_med_state = 'arrive_stock'

    def action_tanger_med_sortie_port(self):
        for rec in self:
            rec.write({
                'tanger_med_state': 'sortie_port',
                'date_sortie_port': fields.Date.context_today(rec)
            })

    def action_tanger_med_arrive_stock(self):
        for rec in self:
            rec.write({
                'tanger_med_state': 'arrive_stock',
                'date_arrive_stock': fields.Date.context_today(rec)
            })

    def action_tanger_med_reset(self):
        for rec in self:
            rec.write({
                'tanger_med_state': 'port'
            })
