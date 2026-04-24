from odoo import models, fields, api


class CasaClientAdvance(models.Model):
    _inherit = 'casa.client.advance'

    charge_line_id = fields.Many2one('charges.casa.line', string='Ligne de Charge Casa', ondelete='cascade')


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
            record._create_client_advances()

    def action_draft(self):
        for record in self:
            # Check if any advance is already validated
            advances = self.env['casa.client.advance'].search([('charge_line_id', 'in', record.line_ids.ids)])
            if any(a.state == 'confirmed' for a in advances):
                raise models.ValidationError("Vous ne pouvez pas remettre en brouillon car certaines avances liées ont déjà été validées.")
            
            advances.unlink()
            record.state = 'draft'

    def _create_client_advances(self):
        self.ensure_one()
        for line in self.line_ids:
            if line.amount <= 0:
                continue
            
            # Use search to avoid duplicates if called multiple times or partially confirmed
            existing_advance = self.env['casa.client.advance'].search([('charge_line_id', '=', line.id)], limit=1)
            
            vals = {
                'client_id': self.client_id.id,
                'amount': line.amount,
                'date': self.date,
                'payment_mode': 'charge',
                'comment': line.comment,
                'state': 'draft',
                'charge_line_id': line.id,
            }
            
            if existing_advance:
                existing_advance.write(vals)
            else:
                self.env['casa.client.advance'].create(vals)

