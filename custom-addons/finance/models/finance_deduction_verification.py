from odoo import models, fields, api

class FinanceDeductionVerification(models.Model):
    _name = 'finance.deduction.verification'
    _description = 'Vérification des Déductions'
    _rec_name = 'facture_ref'
    _order = 'id desc'

    # -------------------------------------------------------------------------
    # UI: User Inputs
    # -------------------------------------------------------------------------
    bl = fields.Char(string='BL', required=True)
    facture_ref = fields.Char(string='Réf. Facture', required=True)
    amount_expected = fields.Float(string='Montant Attendu', required=True)
    benif_id = fields.Many2one(
        'finance.benif', 
        string='Bénéficiaire', 
        required=True,
        domain="[('benif_deduction', '=', True)]"
    )

    # -------------------------------------------------------------------------
    # Computed / Readonly Match Data
    # -------------------------------------------------------------------------
    matched_payment_id = fields.Many2one(
        'finance.deduction.payment',
        string='Paiement Trouvé',
        compute='_compute_matching',
        store=True,
        readonly=True
    )

    matched_bl_id = fields.Many2one(
        related='matched_payment_id.bl_id',
        string='BL (Paiement)',
        readonly=True
    )
    
    matched_amount = fields.Float(
        related='matched_payment_id.amount',
        string='Montant (Paiement)',
        readonly=True
    )
    
    matched_facture_ref = fields.Char(
        related='matched_payment_id.operation_ref',
        string='Réf. Facture (Paiement)',
        readonly=True
    )

    # -------------------------------------------------------------------------
    # Analysis Fields
    # -------------------------------------------------------------------------
    difference = fields.Float(
        string='Différence',
        compute='_compute_difference',
        store=True,
        help="Montant Attendu - Montant Paiement"
    )

    state = fields.Selection([
        ('matched_ok', 'Conforme'),
        ('matched_diff', 'Différence'),
        ('not_found', 'Non trouvé'),
    ], string='État', compute='_compute_state', store=True)

    message_info = fields.Char(
        string='Info',
        compute='_compute_state',
        store=True
    )

    # -------------------------------------------------------------------------
    # COMPUTES
    # -------------------------------------------------------------------------
    @api.depends('facture_ref', 'benif_id')
    def _compute_matching(self):
        for rec in self:
            if not rec.facture_ref or not rec.benif_id:
                rec.matched_payment_id = False
                continue

            # Rule: Ref == Ref AND Benif == Benif. 
            # If multiple, take most recent (order='date desc' in deduction model)
            payments = self.env['finance.deduction.payment'].search([
                ('operation_ref', '=', rec.facture_ref),
                ('benif_id', '=', rec.benif_id.id)
            ], order='date desc', limit=1)

            rec.matched_payment_id = payments.id if payments else False

    @api.depends('amount_expected', 'matched_payment_id', 'matched_amount')
    def _compute_difference(self):
        for rec in self:
            if rec.matched_payment_id:
                rec.difference = rec.amount_expected - rec.matched_amount
            else:
                rec.difference = 0.0

    @api.depends('matched_payment_id', 'difference')
    def _compute_state(self):
        for rec in self:
            if not rec.matched_payment_id:
                rec.state = 'not_found'
                rec.message_info = "❌ Facture non trouvée dans les paiements."
            else:
                # Float comparison tolerance could be used here if needed, 
                # but usually strict equality is expected unless currency rounding issues.
                # using float_is_zero or epsilon is safer practice in Odoo.
                if abs(rec.difference) < 0.01:
                    rec.state = 'matched_ok'
                    rec.message_info = "✅ Facture trouvée - Montant OK."
                else:
                    rec.state = 'matched_diff'
                    rec.message_info = f"⚠️ Facture trouvée - Ecart de {rec.difference:,.2f}"

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    def action_view_payment(self):
        self.ensure_one()
        if not self.matched_payment_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'finance.deduction.payment',
            'res_id': self.matched_payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
