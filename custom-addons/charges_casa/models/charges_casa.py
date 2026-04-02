from odoo import models, fields, api

class ChargesCasa(models.Model):
    _name = 'charges.casa'
    _description = 'Charges Casa'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    amount = fields.Float(string='Montant', required=True, tracking=True)
    type = fields.Selection([
        ('transport', 'Transport'),
        ('salaires', 'Salaires'),
        ('autres', 'Autres')
    ], string='Type', required=True, tracking=True)
    
    partner_id = fields.Many2one('res.partner', string='Bénéficiaire', tracking=True)
    user_id = fields.Many2one('res.users', string='Saisi par', default=lambda self: self.env.user, tracking=True, readonly=True)
    commentaires = fields.Text(string='Commentaires')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé')
    ], string='Statut', default='draft', tracking=True)

    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'

    def action_draft(self):
        for record in self:
            record.state = 'draft'
