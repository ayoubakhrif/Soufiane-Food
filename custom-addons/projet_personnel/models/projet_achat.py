from odoo import models, fields, api

class ProjetAchat(models.Model):
    _name = 'projet.achat'
    _description = 'Commande d\'Achat'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence', required=True, copy=False, default=lambda self: 'Nouveau')
    command_number = fields.Char(string='Command', copy=False, readonly=True)
    date = fields.Date(string='Date d\'Achat', required=True, default=fields.Date.context_today)
    date_livraison = fields.Date(string='Date de Livraison')
    line_ids = fields.One2many('projet.stock', 'achat_id', string='Articles Achetés')

    total_prix_achat = fields.Float(string='Total Achat', compute='_compute_totals', store=True)
    total_prix_vente_prevu = fields.Float(string='Total Vente Prévu', compute='_compute_totals', store=True)
    total_benefice_prevu = fields.Float(string='Bénéfice Prévu Total', compute='_compute_totals', store=True)
    total_benefice_percent = fields.Float(string='Bénéfice Prévu %', compute='_compute_totals', store=True)

    @api.depends('line_ids.prix_achat', 'line_ids.prix_vente_prevu', 'line_ids.benefice_prevu', 'line_ids.quantite')
    def _compute_totals(self):
        for record in self:
            record.total_prix_achat = sum(line.prix_achat * line.quantite for line in record.line_ids)
            record.total_prix_vente_prevu = sum(line.prix_vente_prevu * line.quantite for line in record.line_ids)
            record.total_benefice_prevu = sum(line.benefice_prevu * line.quantite for line in record.line_ids)
            record.total_benefice_percent = (record.total_benefice_prevu / record.total_prix_achat) if record.total_prix_achat else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('projet.achat.seq') or 'Nouveau'
        records = super().create(vals_list)
        for record in records:
            if not record.command_number:
                record.command_number = f"Command {record.id}"
        return records

class ProjetStock(models.Model):
    _name = 'projet.stock'
    _description = 'Article en Stock'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    achat_id = fields.Many2one('projet.achat', string='Commande d\'Achat', ondelete='cascade')
    item_id = fields.Many2one('projet.item', string='Article', required=True)
    color_id = fields.Many2one('projet.item.color', string='Couleur', domain="[('item_id', '=', item_id)]")
    
    image = fields.Image(string='Image', compute='_compute_image', store=True)
    
    quantite = fields.Integer(string='Quantité initiale', required=True, default=1)
    quantite_vendue = fields.Integer(string='Quantité Vendue', default=0, readonly=True)
    quantite_restante = fields.Integer(string='Quantité Restante', compute='_compute_quantite', store=True)
    
    prix_achat = fields.Float(string='Prix d\'Achat', required=True, default=0.0)
    prix_vente_prevu = fields.Float(string='Prix de Vente Prévu', required=True, default=0.0)
    benefice_prevu = fields.Float(string='Bénéfice Prévu', compute='_compute_benefice_prevu', store=True)
    benefice_percent = fields.Float(string='Bénéfice %', compute='_compute_benefice_prevu', store=True)
    
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    state = fields.Selection([
        ('in_stock', 'En Stock'),
        ('sold', 'Vendu')
    ], string='Statut', default='in_stock', required=True, tracking=True, compute='_compute_quantite', store=True)

    @api.depends('quantite', 'quantite_vendue')
    def _compute_quantite(self):
        for record in self:
            record.quantite_restante = record.quantite - record.quantite_vendue
            if record.quantite_restante <= 0 and record.quantite > 0:
                record.state = 'sold'
            else:
                record.state = 'in_stock'

    display_name = fields.Char(string='Nom complet', compute='_compute_display_name', store=True)

    @api.depends('item_id', 'color_id', 'achat_id')
    def _compute_display_name(self):
        for record in self:
            color = f" ({record.color_id.name})" if record.color_id else ""
            record.display_name = f"{record.item_id.name or ''}{color} - {record.achat_id.name or ''}"

    @api.depends('item_id.image', 'color_id.image')
    def _compute_image(self):
        for record in self:
            if record.color_id and record.color_id.image:
                record.image = record.color_id.image
            else:
                record.image = record.item_id.image

    @api.depends('prix_achat', 'prix_vente_prevu')
    def _compute_benefice_prevu(self):
        for record in self:
            record.benefice_prevu = record.prix_vente_prevu - record.prix_achat
            record.benefice_percent = (record.benefice_prevu / record.prix_achat) if record.prix_achat else 0.0
