from odoo import models, fields, api

class ProjetVente(models.Model):
    _name = 'projet.vente'
    _description = 'Commande de Vente'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence', required=True, copy=False, default=lambda self: 'Nouveau')
    command_number = fields.Char(string='Command', copy=False, readonly=True)
    date = fields.Date(string='Date de Vente', required=True, default=fields.Date.context_today)
    line_ids = fields.One2many('projet.vente.line', 'vente_id', string='Articles Vendus')
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Validé')
    ], string='Statut', default='draft', required=True, tracking=True)

    total_prix_vente = fields.Float(string='Total Vente', compute='_compute_totals', store=True)
    total_benefice_reel = fields.Float(string='Bénéfice Réel Total', compute='_compute_totals', store=True)
    total_benefice_percent = fields.Float(string='Bénéfice Réel %', compute='_compute_totals', store=True)

    @api.depends('line_ids.prix_vente', 'line_ids.benefice_reel')
    def _compute_totals(self):
        for record in self:
            record.total_prix_vente = sum(record.line_ids.mapped('prix_vente'))
            record.total_benefice_reel = sum(record.line_ids.mapped('benefice_reel'))
            record.total_benefice_percent = (record.total_benefice_reel / record.total_prix_vente) if record.total_prix_vente else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('projet.vente.seq') or 'Nouveau'
        records = super().create(vals_list)
        for record in records:
            if not record.command_number:
                record.command_number = f"Command {record.id}"
        return records

    def action_validate(self):
        for record in self:
            for line in record.line_ids:
                if line.stock_id:
                    line.stock_id.state = 'sold'
            record.state = 'done'

class ProjetVenteLine(models.Model):
    _name = 'projet.vente.line'
    _description = 'Ligne de Vente'

    vente_id = fields.Many2one('projet.vente', string='Commande de Vente', ondelete='cascade')
    stock_id = fields.Many2one('projet.stock', string='Article en Stock', required=True, domain="[('state', '=', 'in_stock')]")
    
    item_id = fields.Many2one('projet.item', related='stock_id.item_id', string='Article', readonly=True)
    color_id = fields.Many2one('projet.item.color', related='stock_id.color_id', string='Couleur', readonly=True)
    
    prix_achat = fields.Float(related='stock_id.prix_achat', string='Prix d\'Achat', readonly=True)
    prix_vente = fields.Float(string='Prix de Vente', required=True, default=0.0)
    benefice_reel = fields.Float(string='Bénéfice Réel', compute='_compute_benefice_reel', store=True)
    benefice_percent = fields.Float(string='Bénéfice %', compute='_compute_benefice_reel', store=True)

    @api.onchange('stock_id')
    def _onchange_stock_id(self):
        if self.stock_id:
            self.prix_vente = self.stock_id.prix_vente_prevu

    @api.depends('prix_vente', 'prix_achat')
    def _compute_benefice_reel(self):
        for record in self:
            record.benefice_reel = record.prix_vente - record.prix_achat
            record.benefice_percent = (record.benefice_reel / record.prix_achat) if record.prix_achat else 0.0
