from odoo import models, fields, api


class TresoreriePaiement(models.Model):
    _name = 'tresorerie.paiement'
    _description = 'Paiement (Trésorerie)'
    _order = 'create_date desc'

    client_id = fields.Many2one(
        'tresorerie.client',
        string='Client',
        required=True,
        ondelete='restrict',
    )

    payment_type = fields.Selection([
        ('especes', 'Espèces'),
        ('cheque', 'Chèques'),
    ], string='Type de paiement', required=True, default='especes')

    date = fields.Date(
        string='Date du paiement',
        default=fields.Date.context_today,
        required=True,
    )

    # ------------------------------------------------------------------
    # Espèces: simple flat amount (editable, used when type = especes)
    # ------------------------------------------------------------------
    amount_especes = fields.Float(
        string='Montant',
        digits=(10, 2),
    )

    # ------------------------------------------------------------------
    # Chèques: detail lines + computed total
    # ------------------------------------------------------------------
    cheque_line_ids = fields.One2many(
        'tresorerie.paiement.cheque.line',
        'paiement_id',
        string='Chèques / Effets',
    )

    # Kept for backwards-compatibility and used by sortie validations.
    # For especes: equals amount_especes.
    # For cheques: equals sum of lines.
    amount = fields.Float(
        string='Montant total',
        compute='_compute_amount',
        store=True,
        digits=(10, 2),
    )

    # Legacy single-date field kept for sortie domain filtering.
    # For especes it remains editable; for cheques it is hidden
    # (each line carries its own date).
    check_date = fields.Date(string='Date du chèque')

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends('payment_type', 'amount_especes', 'cheque_line_ids.amount')
    def _compute_amount(self):
        for rec in self:
            if rec.payment_type == 'cheque':
                rec.amount = sum(rec.cheque_line_ids.mapped('amount'))
            else:
                rec.amount = rec.amount_especes

    # ------------------------------------------------------------------
    # Onchange helpers
    # ------------------------------------------------------------------
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        """Clear cheque lines or especes amount when switching type."""
        if self.payment_type == 'especes':
            self.cheque_line_ids = [(5, 0, 0)]
        else:
            self.amount_especes = 0.0
