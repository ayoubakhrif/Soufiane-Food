from odoo import models, fields, api, _

class GestionBuffet(models.Model):
    _name = 'gestion.buffet'
    _description = 'Gestion des Buffets'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, index=True, default=lambda self: _('Nouveau'))
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string='Statut', default='draft', tracking=True)

    client_name = fields.Char(string='Client (Personne)', required=True, tracking=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    
    place_id = fields.Many2one('buffet.place', string='Lieu', tracking=True)
    pack_id = fields.Many2one('buffet.pack', string='Pack', tracking=True)
    
    nbr_personne = fields.Integer(string='Nombre de personnes', required=True, default=1, tracking=True)
    prix_personne = fields.Float(string='Prix par personne', required=True, tracking=True)
    avance = fields.Float(string='Avance', tracking=True)

    composant_ids = fields.One2many('buffet.composant.line', 'buffet_id', string='Composants')
    charge_ids = fields.One2many('buffet.charge', 'buffet_id', string='Charges')

    # Computed KPIs
    total_revenu = fields.Float(string='Revenu Total', compute='_compute_totals', store=True, tracking=True)
    reste_a_payer = fields.Float(string='Reste à Payer', compute='_compute_totals', store=True)
    total_charges = fields.Float(string='Coût Charges', compute='_compute_totals', store=True)
    benefice = fields.Float(string='Bénéfice', compute='_compute_totals', store=True, tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nouveau')) == _('Nouveau'):
            vals['name'] = self.env['ir.sequence'].next_by_code('gestion.buffet') or _('Nouveau')
        return super().create(vals)

    @api.onchange('pack_id')
    def _onchange_pack_id(self):
        if self.pack_id:
            self.prix_personne = self.pack_id.price_person

    @api.depends('nbr_personne', 'prix_personne', 'avance', 'charge_ids.amount')
    def _compute_totals(self):
        for rec in self:
            revenu = rec.nbr_personne * rec.prix_personne
            charges = sum(rec.charge_ids.mapped('amount'))
            
            rec.total_revenu = revenu
            rec.reste_a_payer = revenu - rec.avance
            rec.total_charges = charges
            rec.benefice = revenu - charges

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'


class BuffetComposantLine(models.Model):
    _name = 'buffet.composant.line'
    _description = 'Ligne Composant'

    buffet_id = fields.Many2one('gestion.buffet', string='Buffet', ondelete='cascade')
    composant_id = fields.Many2one('buffet.composant', string='Composant', required=True)
    qty = fields.Float(string='Nombre', required=True, default=1.0)

class BuffetCharge(models.Model):
    _name = 'buffet.charge'
    _description = 'Charge de Buffet'

    buffet_id = fields.Many2one('gestion.buffet', string='Buffet', ondelete='cascade')
    name = fields.Char(string='Commentaire', required=True)
    categorie = fields.Selection([
        ('buvette', 'Buvette'),
        ('fournisseur', 'Fournisseur'),
        ('hamala', 'Hamala'),
        ('serviants', 'Serviants'),
        ('transport', 'Transport'),
    ], string='Catégorie', required=True)
    amount = fields.Float(string='Prix', required=True, default=0.0)
