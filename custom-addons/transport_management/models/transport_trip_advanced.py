from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class TransportTripAdvanced(models.Model):
    _name = 'transport.trip.advanced'
    _description = 'Voyage Avancé'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    date = fields.Date(string='Date de voyage', required=True, default=fields.Date.context_today)
    driver_id = fields.Many2one('transport.driver', string='Chauffeur', required=True, tracking=True)
    destination_id = fields.Many2one('transport.destination', string='Destination', required=True, tracking=True)
    
    going_price = fields.Float(string='Prix allée', tracking=True)
    returning_price = fields.Float(string='Prix de retour', tracking=True)
    return_type = fields.Selection([
        ('interne', 'Retour interne'),
        ('externe', 'Retour externe')
    ], string='Type de retour', tracking=True)
    
    charge_fuel = fields.Float(string='Gazoil', tracking=True)
    charge_driver = fields.Float(string='Déplacement Chauffeur', tracking=True)
    charge_adblue = fields.Float(string='AdBlue', tracking=True)
    charge_mixed = fields.Float(string='Mixe (A préciser sur commentaire)', tracking=True)
    note = fields.Text(string='Commentaire (Mixe)')
    
    total_price = fields.Float(string='Prix allée retour', compute='_compute_totals', store=True)
    total_amount = fields.Float(string='Montant des charges', compute='_compute_totals', store=True)
    profit = fields.Float(string='Bénéfice', compute='_compute_totals', store=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('validated', 'Validé')
    ], string='État', default='draft', required=True, tracking=True)

    @api.depends('going_price', 'returning_price', 'charge_fuel', 'charge_driver', 'charge_adblue', 'charge_mixed')
    def _compute_totals(self):
        for rec in self:
            rec.total_price = rec.going_price + rec.returning_price
            rec.total_amount = rec.charge_fuel + rec.charge_driver + rec.charge_adblue + rec.charge_mixed
            rec.profit = rec.total_price - rec.total_amount

    def action_confirm(self):
        for rec in self:
            if rec.destination_id.mandatory_return:
                if rec.returning_price <= 0:
                    raise ValidationError(_("Cette destination exige un retour. Veuillez saisir un prix de retour."))
                if not rec.return_type:
                    raise ValidationError(_("Veuillez sélectionner le type de retour (Interne/Externe)."))
            rec.state = 'confirmed'

    def action_validate(self):
        for rec in self:
            if rec.charge_mixed > 0 and not rec.note:
                raise ValidationError(_("Veuillez spécifier un commentaire pour les charges mixtes."))
            rec.state = 'validated'
            
    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
