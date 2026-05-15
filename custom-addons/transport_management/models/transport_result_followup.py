from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class TransportResultFollowup(models.Model):
    _name = 'transport.result.followup'
    _description = 'Suivi des Résultats Transport'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _sql_constraints = [
        ('unique_type', 'UNIQUE(type)', 'Un seul suivi par type est autorisé ! Un suivi avec ce type existe déjà.'),
    ]

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default=lambda self: _('Suivi des résultats'))
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True, tracking=True)
    
    total_profit = fields.Float(
        string='Bénéfice Total', 
        compute='_compute_total_profit', 
        store=False, # Computed on the fly to always reflect current state
        tracking=True
    )
    
    distributed_amount = fields.Float(
        string='Montant Distribué', 
        compute='_compute_amounts', 
        store=False,
    )
    
    remaining_amount = fields.Float(
        string='Reste à Distribuer', 
        compute='_compute_amounts', 
        store=False,
    )

    type = fields.Selection([
        ('transport', 'Transport'),
        ('gasoil', 'Gasoil'),
        ('transport_remorque', 'Transport Remorques')
    ], string='Type', required=True, default='transport', tracking=True)
    
    line_ids = fields.One2many(
        'transport.result.line', 
        'followup_id', 
        string='Lignes de distribution'
    )

    @api.depends('type', 'line_ids.amount')
    def _compute_total_profit(self):
        for rec in self:
            if rec.type == 'gasoil':
                records = self.env['gasoil.sale'].search([])
            elif rec.type == 'transport_remorque':
                records = self.env['transport.trip.remorque'].search([])
            else:
                records = self.env['transport.trip'].search([])
            rec.total_profit = sum(records.mapped('profit'))

    @api.depends('type', 'line_ids.amount')
    def _compute_amounts(self):
        for rec in self:
            distributed = sum(rec.line_ids.mapped('amount'))
            rec.distributed_amount = distributed
            rec.remaining_amount = rec.total_profit - rec.distributed_amount

    def action_refresh(self):
        """Refreshes the view to update computed fields."""
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

class TransportResultLine(models.Model):
    _name = 'transport.result.line'
    _description = 'Ligne de distribution Transport'

    followup_id = fields.Many2one('transport.result.followup', string='Suivi', required=True, ondelete='cascade')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    amount = fields.Float(string='Montant', required=True)
    
    paid_to = fields.Selection([
        ('amine', 'Amine'),
        ('imane', 'Imane'),
        ('banque', 'Banque')
    ], string='Payé à', required=True)
    
    type = fields.Selection(related='followup_id.type', store=True, readonly=True)
    
    comment = fields.Char(string='Commentaire')

    @api.constrains('amount')
    def _check_amount(self):
        for line in self:
            if line.amount <= 0:
                raise ValidationError(_("Le montant doit être supérieur à 0."))
            
            # Recompute remaining of the parent to be sure
            # Actually, constraint might run before parent compute is flushed/updated in UI context
            # So we check against (total_profit - ALREADY_DISTRIBUTED_WITHOUT_THIS_LINE - THIS_LINE)
            
            # Simple check: (Parent Total Profit) < (Sum of all lines including this one)
            parent = line.followup_id
            # Force recompute of total profit to be sure
            parent._compute_total_profit()
            
            # Calculate total distributed including current changes
            # We can use the parent's relation which should include this new/modified record in memory
            total_distributed = sum(parent.line_ids.mapped('amount'))
            
            if total_distributed > parent.total_profit:
                remaining = parent.total_profit - (total_distributed - line.amount)
                raise ValidationError(
                    _("Opération bloquée !\n"
                      "Le montant saisi ({saisi}) dépasse le montant restant ({reste}).\n"
                      "Bénéfice Total: {total}").format(
                        saisi=line.amount,
                        reste=remaining,
                        total=parent.total_profit
                    )
                )
