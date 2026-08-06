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
    
    total_gasoil_sale = fields.Float(
        string='Total Vente Gazoil',
        compute='_compute_total_profit',
        store=False,
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
            rec.total_gasoil_sale = 0.0
            if rec.type == 'gasoil':
                records = self.env['gasoil.sale'].search([])
                rec.total_gasoil_sale = sum(records.mapped('amount'))
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
            if rec.type == 'gasoil':
                rec.remaining_amount = rec.total_gasoil_sale - rec.distributed_amount
            else:
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
    _order = 'date desc, id desc'

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

    @api.onchange('amount')
    def _onchange_amount(self):
        if self.amount < 0:
            return {
                'warning': {
                    'title': _("Attention"),
                    'message': _("Le montant devrait être positif.")
                }
            }
            
        if self.followup_id:
            parent = self.followup_id
            # Force recompute just in case
            parent._compute_total_profit()
            
            total_distributed = sum(parent.line_ids.mapped('amount'))
            max_amount = parent.total_gasoil_sale if parent.type == 'gasoil' else parent.total_profit
            
            if total_distributed > max_amount:
                remaining = max_amount - (total_distributed - self.amount)
                return {
                    'warning': {
                        'title': _("Dépassement"),
                        'message': _("Attention ! Le montant saisi ({saisi}) dépasse le montant restant ({reste}).\n"
                                     "Vous pouvez quand même sauvegarder.").format(
                            saisi=self.amount,
                            reste=remaining
                        )
                    }
                }
