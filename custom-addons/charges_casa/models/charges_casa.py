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
    
    client_id = fields.Many2one('casa.client', string='Client', tracking=True)
    ville = fields.Selection([
        ('agadir', 'Agadir'),
        ('tanger', 'Tanger'),
        ('marrakech', 'Marrakech'),
        ('kenitra', 'Kenitra'),
        ('casa', 'Casa')
    ], string='Ville', tracking=True)
    user_id = fields.Many2one('res.users', string='Saisi par', default=lambda self: self.env.user, tracking=True, readonly=True)
    commentaires = fields.Char(string='Commentaires')
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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.client_id:
                record._create_client_advance()
        return records

    def write(self, vals):
        if 'client_id' in vals:
            old_clients = {rec.id: rec.client_id for rec in self}
            res = super().write(vals)
            for rec in self:
                if rec.client_id and rec.client_id != old_clients.get(rec.id):
                    rec._create_client_advance()
            return res
        return super().write(vals)

    def _create_client_advance(self):
        self.ensure_one()
        self.env['casa.client.advance'].create({
            'client_id': self.client_id.id,
            'amount': self.amount,
            'date': self.date,
            'payment_mode': 'charge',
            'comment': self.commentaires,
            'state': 'draft',
        })
