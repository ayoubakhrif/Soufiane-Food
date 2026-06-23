from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class FinanceMargloryPayment(models.Model):
    _name = 'finance.marglory.payment'
    _description = 'Paiement Marglory'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'cheque_id'

    date = fields.Date(string='Date de paiement', default=fields.Date.context_today, required=True, tracking=True)
    dossier_reglement = fields.Char(string="Réglement N°", tracking=True)
    
    physical_cheque_id = fields.Many2one(
        'finance.cheque.physical',
        string='Chèque',
        domain="[('benif_id.name', 'ilike', 'MARGLORY')]",
        tracking=True
    )

    cheque_id = fields.Many2one(
        'datacheque',
        string='Chèque (Ancien)',
        required=False,
        tracking=True
    )
    
    marglory_ids = fields.Many2many(
        'finance.marglory',
        'finance_marglory_payment_rel',
        'payment_id',
        'marglory_id',
        string='Factures Marglory',
        domain="[('payment_id','=',False)]",
        tracking=True
    )

    amount_total = fields.Float(
        string='Total Factures',
        compute='_compute_amount_total',
        store=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
    ], string='Status', default='draft', tracking=True)

    cheque_amount = fields.Float(
        related='physical_cheque_id.amount_total',
        string='Montant du chèque',
        readonly=True,
        store=True
    )

    @api.depends('marglory_ids', 'marglory_ids.amount')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.marglory_ids.mapped('amount'))

    def action_confirm(self):
        for rec in self:
            if not rec.marglory_ids:
                raise ValidationError("Veuillez sélectionner au moins une facture Marglory.")

            if not rec.cheque_amount:
                raise ValidationError("Le montant du chèque est vide ou zéro.")

            difference = rec.cheque_amount - rec.amount_total

            # Using a small epsilon for float comparison safety, though currency usually 2 decimals
            if abs(difference) > 0.01:
                raise ValidationError(
                    _(
                        "Montant incohérent ❌\n\n"
                        "Montant du chèque : %(chq)s MAD\n"
                        "Total des factures : %(inv)s MAD\n"
                        "Différence : %(diff)s MAD\n\n"
                        "Veuillez corriger avant de confirmer."
                    ) % {
                        'chq': "{:,.2f}".format(rec.cheque_amount),
                        'inv': "{:,.2f}".format(rec.amount_total),
                        'diff': "{:,.2f}".format(difference),
                    }
                )


            # Lier les factures au paiement
            rec.marglory_ids.write({'payment_id': rec.id})

            rec.state = 'confirmed'

    def action_draft(self):
        self.write({'state': 'draft'})
