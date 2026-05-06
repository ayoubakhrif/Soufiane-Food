from odoo import models, fields, api


class TresoreriePaiement(models.Model):
    _name = 'tresorerie_chq.paiement'
    _description = 'Paiement (Trésorerie Chèques & Effets)'
    _order = 'create_date desc'

    client_id = fields.Many2one(
        'tresorerie_chq.client',
        string='Client',
        required=True,
        ondelete='restrict',
    )

    payment_type = fields.Selection([
        ('cheque', 'Chèques'),
        ('effet', 'Effets'),
    ], string='Type de paiement', required=True, default='cheque')

    is_soufiane = fields.Boolean(
        compute='_compute_is_soufiane',
        string='Est Soufiane',
    )

    date = fields.Date(
        string='Date du paiement',
        default=fields.Date.context_today,
        required=True,
    )

    # ------------------------------------------------------------------
    # Chèques et Effets: separate detail lines
    # ------------------------------------------------------------------
    cheque_line_ids = fields.One2many(
        'tresorerie_chq.paiement.cheque.line',
        'paiement_id',
        string='Chèques',
    )

    effet_line_ids = fields.One2many(
        'tresorerie_chq.paiement.effet.line',
        'paiement_id',
        string='Effets',
    )

    # Computed total amount depending on payment type
    amount = fields.Float(
        string='Montant total',
        compute='_compute_amount',
        store=True,
        digits=(10, 2),
    )

    # Computed single check date for backward/sortie query compatibility
    check_date = fields.Date(
        string='Date d\'échéance',
        compute='_compute_check_date',
        store=True,
    )

    # ------------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------------
    @api.depends('client_id.name')
    def _compute_is_soufiane(self):
        for rec in self:
            rec.is_soufiane = rec.client_id and rec.client_id.name == 'Soufiane'

    @api.depends('payment_type', 'cheque_line_ids.amount', 'effet_line_ids.amount')
    def _compute_amount(self):
        for rec in self:
            if rec.payment_type == 'cheque':
                rec.amount = sum(rec.cheque_line_ids.mapped('amount'))
            elif rec.payment_type == 'effet':
                rec.amount = sum(rec.effet_line_ids.mapped('amount'))
            else:
                rec.amount = 0.0

    @api.depends('payment_type', 'cheque_line_ids.check_date', 'effet_line_ids.check_date')
    def _compute_check_date(self):
        for rec in self:
            dates = []
            if rec.payment_type == 'cheque' and rec.cheque_line_ids:
                dates = [l.check_date for l in rec.cheque_line_ids if l.check_date]
            elif rec.payment_type == 'effet' and rec.effet_line_ids:
                dates = [l.check_date for l in rec.effet_line_ids if l.check_date]
            rec.check_date = min(dates) if dates else False
