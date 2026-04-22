from odoo import models, fields, api


class ChargesCasaLine(models.Model):
    _name = 'charges.casa.line'
    _description = 'Ligne de Charge Casa'

    charge_id = fields.Many2one('charges.casa', string='Charge', required=True, ondelete='cascade')
    type = fields.Selection([
        ('transport', 'Transport'),
        ('salaires', 'Salaires'),
        ('autres', 'Autres'),
    ], string='Type', required=True)
    amount = fields.Float(string='Montant', required=True)
    comment = fields.Char(string='Commentaire')


class ChargesCasa(models.Model):
    _name = 'charges.casa'
    _description = 'Charges Casa'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    client_id = fields.Many2one('casa.client', string='Client', tracking=True)
    ville = fields.Selection([
        ('agadir', 'Agadir'),
        ('tanger', 'Tanger'),
        ('marrakech', 'Marrakech'),
        ('kenitra', 'Kenitra'),
        ('casa', 'Casa'),
    ], string='Ville', tracking=True)
    user_id = fields.Many2one('res.users', string='Saisi par', default=lambda self: self.env.user, tracking=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
    ], string='Statut', default='draft', tracking=True)

    line_ids = fields.One2many('charges.casa.line', 'charge_id', string='Lignes de Charges')

    total_amount = fields.Float(string='Total', compute='_compute_total_amount', store=True)
    total_transport = fields.Float(string='Total Transport', compute='_compute_total_amount', store=True)
    total_salaires = fields.Float(string='Total Salaires', compute='_compute_total_amount', store=True)
    total_autres = fields.Float(string='Total Autres', compute='_compute_total_amount', store=True)

    @api.depends('line_ids.amount', 'line_ids.type')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.line_ids.mapped('amount'))
            record.total_transport = sum(record.line_ids.filtered(lambda l: l.type == 'transport').mapped('amount'))
            record.total_salaires = sum(record.line_ids.filtered(lambda l: l.type == 'salaires').mapped('amount'))
            record.total_autres = sum(record.line_ids.filtered(lambda l: l.type == 'autres').mapped('amount'))

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
                record._create_client_advances()
        return records

    def write(self, vals):
        if 'client_id' in vals:
            old_clients = {rec.id: rec.client_id for rec in self}
            res = super().write(vals)
            for rec in self:
                if rec.client_id and rec.client_id != old_clients.get(rec.id):
                    rec._create_client_advances()
            return res
        return super().write(vals)

    def _create_client_advances(self):
        self.ensure_one()
        for line in self.line_ids:
            self.env['casa.client.advance'].create({
                'client_id': self.client_id.id,
                'amount': line.amount,
                'date': self.date,
                'payment_mode': 'charge',
                'comment': line.comment,
                'state': 'draft',
            })
