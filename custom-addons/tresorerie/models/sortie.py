from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class TresorerieSortie(models.Model):
    _name = 'tresorerie.sortie'
    _description = 'Sortie (Trésorerie)'
    _order = 'date desc, id desc'

    # -------------------------------------------------------------------------
    # Basic fields
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Référence',
        readonly=True,
        default='/',
        copy=False,
    )
    date = fields.Date(
        string='Date de sortie',
        default=fields.Date.context_today,
        required=True,
    )
    payment_type = fields.Selection(
        [('especes', 'Espèces'), ('cheque', 'Chèque')],
        string='Mode de paiement',
        required=True,
        default='especes',
    )
    client_id = fields.Many2one(
        'tresorerie.client',
        string='Client',
        ondelete='restrict',
    )
    amount = fields.Float(
        string='Montant (MAD)',
        required=True,
        digits=(10, 2),
    )
    note = fields.Text(string='Remarques / Référence')
    state = fields.Selection(
        [('draft', 'Brouillon'), ('confirmed', 'Confirmé')],
        string='État',
        default='draft',
        readonly=True,
        copy=False,
        tracking=True,
    )

    # -------------------------------------------------------------------------
    # Computed readonly info fields (for UI display)
    # -------------------------------------------------------------------------
    balance_especes = fields.Float(
        string='Solde Espèces disponible (MAD)',
        compute='_compute_balances',
        digits=(10, 2),
    )
    balance_cheques = fields.Float(
        string='Solde Chèques disponible (MAD)',
        compute='_compute_balances',
        digits=(10, 2),
    )
    client_cheque_balance = fields.Float(
        string='Solde chèques client (MAD)',
        compute='_compute_client_cheque_balance',
        digits=(10, 2),
    )

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------
    @api.depends('state', 'amount', 'payment_type')
    def _compute_balances(self):
        """
        Separate balances per payment type.
        Espèces balance  = Σ paiements(especes) - Σ confirmed sorties(especes)
        Chèques balance  = Σ paiements(cheque)  - Σ confirmed sorties(cheque)
        Cheque entries do NOT add to the espèces reserve and vice-versa.
        """
        # --- Entries split by type ---
        paiements = self.env['tresorerie.paiement'].search([])
        total_especes_in = sum(p.amount for p in paiements if p.payment_type == 'especes')
        total_cheques_in = sum(p.amount for p in paiements if p.payment_type == 'cheque')

        # --- Confirmed sorties split by type ---
        all_confirmed = self.env['tresorerie.sortie'].search([('state', '=', 'confirmed')])

        for rec in self:
            especes_out = sum(s.amount for s in all_confirmed
                              if s.payment_type == 'especes' and s.id != rec.id)
            cheques_out = sum(s.amount for s in all_confirmed
                              if s.payment_type == 'cheque' and s.id != rec.id)
            rec.balance_especes = total_especes_in - especes_out
            rec.balance_cheques = total_cheques_in - cheques_out

    @api.depends('client_id', 'state', 'amount')
    def _compute_client_cheque_balance(self):
        """
        Client cheque balance = sum of cheques in paiements for this client
        with check_date <= today  MINUS  sum of confirmed sorties for this client.
        """
        today = fields.Date.today()
        for rec in self:
            if not rec.client_id:
                rec.client_cheque_balance = 0.0
                continue

            # Cheques received from this client with surpassed due date
            cheques = self.env['tresorerie.paiement'].search([
                ('client_id', '=', rec.client_id.id),
                ('payment_type', '=', 'cheque'),
                ('check_date', '<=', today),
            ])
            total_cheques = sum(c.amount for c in cheques)

            # Already confirmed sorties attributed to this client
            sorties = self.env['tresorerie.sortie'].search([
                ('client_id', '=', rec.client_id.id),
                ('state', '=', 'confirmed'),
            ])
            already_used = sum(s.amount for s in sorties if s.id != rec.id)

            rec.client_cheque_balance = total_cheques - already_used

    # -------------------------------------------------------------------------
    # Domain helper: clients with at least one overdue cheque
    # -------------------------------------------------------------------------
    @api.model
    def _domain_clients_with_overdue_cheques(self):
        today = fields.Date.today()
        paiements = self.env['tresorerie.paiement'].search([
            ('payment_type', '=', 'cheque'),
            ('check_date', '<=', today),
        ])
        client_ids = paiements.mapped('client_id').ids
        return [('id', 'in', client_ids)]

    # -------------------------------------------------------------------------
    # Onchange helpers
    # -------------------------------------------------------------------------
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        """Reset client when switching to especes."""
        if self.payment_type == 'especes':
            self.client_id = False

    @api.onchange('client_id')
    def _onchange_client_id(self):
        """Recompute balances when client changes."""
        self._compute_client_cheque_balance()

    # -------------------------------------------------------------------------
    # Constraints / Validations
    # -------------------------------------------------------------------------
    @api.constrains('amount', 'payment_type', 'client_id', 'state')
    def _check_amounts(self):
        for rec in self:
            if rec.state != 'confirmed':
                continue

            # ----------------------------------------------------------------
            # Fetch entries & confirmed sorties split by payment type
            # ----------------------------------------------------------------
            paiements = self.env['tresorerie.paiement'].search([])
            total_especes_in = sum(p.amount for p in paiements if p.payment_type == 'especes')
            total_cheques_in = sum(p.amount for p in paiements if p.payment_type == 'cheque')

            all_confirmed = self.env['tresorerie.sortie'].search([
                ('state', '=', 'confirmed'),
                ('id', '!=', rec.id),
            ])
            especes_out = sum(s.amount for s in all_confirmed if s.payment_type == 'especes')
            cheques_out = sum(s.amount for s in all_confirmed if s.payment_type == 'cheque')

            available_especes = total_especes_in - especes_out
            available_cheques = total_cheques_in - cheques_out

            # ----------------------------------------------------------------
            # 1. Per-type trésorerie balance check
            # ----------------------------------------------------------------
            if rec.payment_type == 'especes':
                if rec.amount > available_especes:
                    raise ValidationError(
                        f"❌ Solde Espèces insuffisant en trésorerie !\n"
                        f"Montant demandé  : {rec.amount:,.2f} MAD\n"
                        f"Solde Espèces    : {available_especes:,.2f} MAD"
                    )

            elif rec.payment_type == 'cheque':
                # 1a. Global chèque reserve check
                if rec.amount > available_cheques:
                    raise ValidationError(
                        f"❌ Solde Chèques insuffisant en trésorerie !\n"
                        f"Montant demandé  : {rec.amount:,.2f} MAD\n"
                        f"Solde Chèques    : {available_cheques:,.2f} MAD"
                    )

                # 1b. Client-specific cheque balance check
                if not rec.client_id:
                    raise ValidationError(
                        "❌ Veuillez sélectionner un client pour un paiement par chèque."
                    )

                today = fields.Date.today()
                client_cheques = self.env['tresorerie.paiement'].search([
                    ('client_id', '=', rec.client_id.id),
                    ('payment_type', '=', 'cheque'),
                    ('check_date', '<=', today),
                ])
                total_client_cheques = sum(c.amount for c in client_cheques)

                if total_client_cheques == 0:
                    raise ValidationError(
                        f"❌ Le client {rec.client_id.name} n'a aucun chèque échu disponible."
                    )

                client_sorties = self.env['tresorerie.sortie'].search([
                    ('client_id', '=', rec.client_id.id),
                    ('payment_type', '=', 'cheque'),
                    ('state', '=', 'confirmed'),
                    ('id', '!=', rec.id),
                ])
                already_used = sum(s.amount for s in client_sorties)
                client_available = total_client_cheques - already_used

                if rec.amount > client_available:
                    raise ValidationError(
                        f"❌ Montant supérieur au solde chèques de {rec.client_id.name} !\n"
                        f"Montant demandé          : {rec.amount:,.2f} MAD\n"
                        f"Solde chèques disponible : {client_available:,.2f} MAD"
                    )

    @api.constrains('payment_type', 'client_id')
    def _check_cheque_requires_client(self):
        for rec in self:
            if rec.payment_type == 'cheque' and not rec.client_id:
                raise ValidationError(
                    "❌ Un paiement par chèque nécessite la sélection d'un client."
                )

    # -------------------------------------------------------------------------
    # Workflow buttons
    # -------------------------------------------------------------------------
    def action_confirm(self):
        """Confirm the sortie — this triggers amount validations via constrains."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError("Seuls les enregistrements en brouillon peuvent être confirmés.")
            if rec.amount <= 0:
                raise ValidationError("❌ Le montant doit être supérieur à 0.")
            rec.state = 'confirmed'
            # Assign a sequence reference
            if rec.name == '/':
                rec.name = self.env['ir.sequence'].next_by_code('tresorerie.sortie') or '/'

    def action_reset_draft(self):
        """Reset a confirmed sortie back to draft (manager only)."""
        for rec in self:
            rec.state = 'draft'

    # -------------------------------------------------------------------------
    # Create override — auto-assign sequence
    # -------------------------------------------------------------------------
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('tresorerie.sortie') or '/'
        return super().create(vals)
