from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class FinanceSutraPayment(models.Model):
    _name = 'finance.sutra.payment'
    _description = 'Paiement Sutra'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'cheque_id'

    date = fields.Date(string='Date de paiement', default=fields.Date.context_today, required=True, tracking=True)
    
    cheque_id = fields.Many2one(
        'datacheque',
        string='Chèque',
        domain="[('benif_id.name', 'ilike', 'SUTRA')]",
        required=True,
        tracking=True
    )
    
    sutra_ids = fields.Many2many(
        'finance.sutra',
        'finance_sutra_payment_rel',
        'payment_id',
        'sutra_id',
        string='Factures Sutra',
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
        related='cheque_id.amount',
        string='Montant du chèque',
        readonly=True,
        store=True
    )

    @api.depends('sutra_ids.total')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.sutra_ids.mapped('total'))

    def action_confirm(self):
        for rec in self:
            if not rec.sutra_ids:
                raise ValidationError("Veuillez sélectionner au moins une facture Sutra.")

            # Sécurité : montant chèque obligatoire
            if not rec.cheque_amount:
                raise ValidationError("Le montant du chèque est vide.")

            # Comparaison montants
            difference = rec.cheque_amount - rec.amount_total

            if abs(difference) > 0.01:
                raise ValidationError(
                    _(
                        "Montant incohérent ❌\n\n"
                        "Montant du chèque : %(chq)s MAD\n"
                        "Total des factures : %(inv)s MAD\n"
                        "Différence : %(diff)s MAD\n\n"
                        "Veuillez corriger avant de confirmer."
                    ) % {
                        'chq': rec.cheque_amount,
                        'inv': rec.amount_total,
                        'diff': round(difference, 2),
                    }
                )


            # Lier les factures au paiement
            rec.sutra_ids.write({'payment_id': rec.id})

            rec.state = 'confirmed'

    def action_draft(self):
        self.write({'state': 'draft'})
