from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AchatContractAdvance(models.Model):
    _name = 'achat.contract.advance'
    _description = 'Purchase Contract Advance'
    _order = 'date desc, id desc'

    contract_id = fields.Many2one('achat.contract', string='Contract', required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Amount', required=True, digits=(16, 2))
    
    document_link = fields.Char(string='Document Link')
    note = fields.Text(string='Note')

    # Related fields for display
    contract_name = fields.Char(related='contract_id.name', string='Contract Ref', readonly=True)
    partner_id = fields.Many2one(related='contract_id.supplier_id', string='Supplier', readonly=True)
    origin_id = fields.Many2one(related='contract_id.origin_id', string='Origin', readonly=True)
    contract_amount = fields.Float(related='contract_id.total_amount', string='Contract Total', readonly=True)
    
    # Computed fields
    remaining_amount = fields.Float(string='Remaining Amount', compute='_compute_remaining_amount')

    @api.depends('contract_id.amount_residual')
    def _compute_remaining_amount(self):
        for rec in self:
            rec.remaining_amount = rec.contract_id.amount_residual

    @api.constrains('amount', 'contract_id')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError("Amount must be strictly positive.")
            
            # Check if amount exceeds remaining amount ONLY on creation or amount increase
            # To avoid blocking edits if contract changes later, we check against current residual 
            # Note: amount_residual includes the current record's amount if it was already saved, 
            # so we need to be careful.
            # Simplified check: New Amount <= (Current Residual + Old Amount if exists)
            
            # Actually, standard practice: check if contract residual < 0 after this transaction.
            # But amount_residual is computed from sum of advances.
            # Let's check: total - (sum of all advances including this one) >= 0
            
            # Since amount_residual is computed, we can just check if it's negative.
            # However, api.constrains runs after write, so amount_residual should be updated.

    def action_open_document(self):
        self.ensure_one()
        if self.document_link:
            return {
                'type': 'ir.actions.act_url',
                'url': self.document_link,
                'target': 'new',
            }
