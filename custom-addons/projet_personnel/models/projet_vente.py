from odoo import models, fields, api
from odoo.exceptions import UserError

class ProjetVente(models.Model):
    _name = 'projet.vente'
    _description = 'Commande de Vente'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence', required=True, copy=False, default=lambda self: 'Nouveau')
    command_number = fields.Char(string='Command', copy=False, readonly=True)
    date = fields.Date(string='Date de Vente', required=True, default=fields.Date.context_today)
    personne_id = fields.Many2one('suivi.personne', string='Acheteur / Personne', tracking=True)
    line_ids = fields.One2many('projet.vente.line', 'vente_id', string='Articles Vendus')
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Validé')
    ], string='Statut', default='draft', required=True, tracking=True)

    is_manager = fields.Boolean(compute='_compute_is_manager')

    total_prix_vente = fields.Float(string='Total Vente', compute='_compute_totals', store=True)
    total_benefice_reel = fields.Float(string='Bénéfice Réel Total', compute='_compute_totals', store=True)
    total_benefice_percent = fields.Float(string='Bénéfice Réel %', compute='_compute_totals', store=True)

    @api.depends_context('uid')
    def _compute_is_manager(self):
        for rec in self:
            rec.is_manager = self.env.user.has_group('projet_personnel.group_manager')

    @api.depends('line_ids.prix_vente', 'line_ids.benefice_reel', 'line_ids.quantite')
    def _compute_totals(self):
        for record in self:
            record.total_prix_vente = sum((line.prix_vente * line.quantite) for line in record.line_ids)
            record.total_benefice_reel = sum(line.benefice_reel for line in record.line_ids)
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

    def write(self, vals):
        if 'state' in vals:
            # Restreindre le changement d'état libre au manager
            if not self.env.user.has_group('projet_personnel.group_manager'):
                raise UserError("Seul un gestionnaire peut modifier librement l'état de la commande.")
            
            for record in self:
                old_state = record.state
                new_state = vals['state']
                if old_state != new_state:
                    if new_state == 'done':
                        # Validation de la commande : mettre à jour les stocks
                        for line in record.line_ids:
                            if line.stock_id:
                                line.stock_id.quantite_vendue += line.quantite
                    elif old_state == 'done' and new_state == 'draft':
                        # Retour en brouillon : annuler l'impact sur les stocks
                        for line in record.line_ids:
                            if line.stock_id:
                                line.stock_id.quantite_vendue -= line.quantite
        return super(ProjetVente, self).write(vals)

    def action_validate(self):
        for record in self:
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
    quantite = fields.Integer(string='Quantité', default=1, required=True)
    benefice_reel = fields.Float(string='Bénéfice Réel', compute='_compute_benefice_reel', store=True)
    benefice_percent = fields.Float(string='Bénéfice %', compute='_compute_benefice_reel', store=True)

    @api.onchange('stock_id')
    def _onchange_stock_id(self):
        if self.stock_id:
            self.prix_vente = self.stock_id.prix_vente_prevu

    @api.depends('prix_vente', 'prix_achat', 'quantite')
    def _compute_benefice_reel(self):
        for record in self:
            record.benefice_reel = (record.prix_vente - record.prix_achat) * record.quantite
            record.benefice_percent = (record.benefice_reel / (record.prix_achat * record.quantite)) if record.prix_achat and record.quantite else 0.0
