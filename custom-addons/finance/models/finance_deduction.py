from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class FinanceDeductionAccount(models.Model):
    _name = 'finance.deduction.account'
    _description = 'Compte de Déduction'
    _rec_name = 'display_name'

    ste_id = fields.Many2one('finance.ste', string='Société', required=True, tracking=True)
    benif_id = fields.Many2one('finance.benif', string='Bénéficiaire', required=True, tracking=True, domain="[('benif_deduction', '=', True)]")
    
    deposit_ids = fields.One2many('finance.deduction.deposit', 'account_id', string='Dépôts')
    payment_ids = fields.One2many('finance.deduction.payment', 'account_id', string='Paiements')
    
    total_deposited = fields.Float(string='Total Déposé', compute='_compute_balance', store=True)
    total_deducted = fields.Float(string='Total Déduit', compute='_compute_balance', store=True)
    balance = fields.Float(string='Solde Restant', compute='_compute_balance', store=True)

    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('unique_ste_benif', 'unique(ste_id, benif_id)', 'Un compte de déduction existe déjà pour ce couple Société / Bénéficiaire.')
    ]

    @api.depends('ste_id', 'benif_id')
    def _compute_display_name(self):
        for rec in self:
            ste = rec.ste_id.name if rec.ste_id else '?'
            benif = rec.benif_id.name if rec.benif_id else '?'
            rec.display_name = f"{ste} ↔ {benif}"

    @api.depends('deposit_ids.amount', 'payment_ids.amount')
    def _compute_balance(self):
        for rec in self:
            total_dep = sum(d.amount for d in rec.deposit_ids)
            total_ded = sum(p.amount for p in rec.payment_ids)
            rec.total_deposited = total_dep
            rec.total_deducted = total_ded
            rec.balance = total_dep - total_ded


class FinanceDeductionDeposit(models.Model):
    _name = 'finance.deduction.deposit'
    _description = 'Dépôt (Avance)'
    _order = 'date desc, id desc'

    account_id = fields.Many2one('finance.deduction.account', string='Compte', required=True, ondelete='cascade')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    amount = fields.Float(string='Montant', required=True)
    reference = fields.Char(string='Référence')
    comment = fields.Text(string='Commentaire')

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError("Le montant du dépôt doit être positif.")


class FinanceDeductionPayment(models.Model):
    _name = 'finance.deduction.payment'
    _description = 'Paiement par Déduction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    # Relation logic: User picks Ste + Benif -> System finds Account
    ste_id = fields.Many2one('finance.ste', string='Société', required=True, tracking=True)
    benif_id = fields.Many2one('finance.benif', string='Bénéficiaire', required=True, tracking=True, domain="[('benif_deduction', '=', True)]")
    
    account_id = fields.Many2one('finance.deduction.account', string='Compte de Déduction', compute='_compute_account_id', store=True, readonly=True)

    date = fields.Date(string='Date Opération', default=fields.Date.context_today, required=True, tracking=True)
    amount = fields.Float(string='Montant Déduit', required=True, tracking=True)
    operation_ref = fields.Char(string='Référence Opération / Facture', required=True, tracking=True)
    note = fields.Text(string='Note')

    @api.depends('ste_id', 'benif_id')
    def _compute_account_id(self):
        for rec in self:
            if rec.ste_id and rec.benif_id:
                account = self.env['finance.deduction.account'].search([
                    ('ste_id', '=', rec.ste_id.id),
                    ('benif_id', '=', rec.benif_id.id)
                ], limit=1)
                rec.account_id = account
            else:
                rec.account_id = False

    @api.model
    def create(self, vals):
        # 1. Resolve Account Check
        ste_id = vals.get('ste_id')
        benif_id = vals.get('benif_id')
        amount = vals.get('amount', 0)

        # Basic Checks
        if amount <= 0:
            raise ValidationError("Le montant de la déduction doit être strictement positif.")

        # Find Account
        account = self.env['finance.deduction.account'].search([
            ('ste_id', '=', ste_id),
            ('benif_id', '=', benif_id)
        ], limit=1)

        if not account:
            # Try to get names for error message
            ste_name = self.env['finance.ste'].browse(ste_id).name
            benif_name = self.env['finance.benif'].browse(benif_id).name
            raise ValidationError(f"Aucun compte de déduction trouvé pour {ste_name} ↔ {benif_name}.\nVeuillez d'abord créer ce compte et y ajouter des fonds.")

        # 2. Strict Balance Check
        # Available = Balance (Stored)
        # Note: If concurrent creating, this might be race-condition prone but Odoo handles transactions.
        # Ideally we compute current balance from DB to be checking against most recent state.
        
        if account.balance < amount:
            raise ValidationError(
                f"🚫 Solde insuffisant pour ce paiement.\n\n"
                f"Compte : {account.display_name}\n"
                f"Solde disponible : {account.balance:,.2f}\n"
                f"Montant demandé : {amount:,.2f}\n\n"
                "Veuillez créditer le compte avant de passer ce paiement."
            )

        return super().create(vals)
