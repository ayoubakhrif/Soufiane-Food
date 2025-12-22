from odoo import models, fields, api, exceptions

class FinanceChequeEncaisse(models.Model):
    _name = 'finance.cheque.encaisse'
    _description = 'Chèque Encaissé'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'cheque_id'
    _order = 'create_date desc'

    ste_id = fields.Many2one('finance.ste', string='Société', required=True, tracking=True)
    benif_id = fields.Many2one('finance.benif', string='Bénéficiaire', required=True, tracking=True)
    
    cheque_id = fields.Many2one(
        'datacheque', 
        string='Chèque', 
        required=True,
        domain="[('ste_id', '=', ste_id), ('benif_id', '=', benif_id), ('date_encaissement', '=', False)]"
    )
    
    # Editable fields to sync
    amount = fields.Float(string='Montant', required=True, tracking=True)
    date_encaissement = fields.Date(string='Date d’encaissement', required=True, tracking=True)
    
    # Store original amount for undo logic
    original_amount = fields.Float(string='Montant Origine', readonly=True)

    # Readonly related fields for display
    journal = fields.Integer(related='cheque_id.journal', string='Journal N°', readonly=True)
    date_emission = fields.Date(related='cheque_id.date_emission', string='Date d’émission', readonly=True)
    date_echeance = fields.Date(related='cheque_id.date_echeance', string='Date d’échéance', readonly=True)

    @api.onchange('ste_id', 'benif_id')
    def _onchange_filter_reset(self):
        """Reset cheque selection if filters change"""
        self.cheque_id = False
        self.amount = 0.0
        self.original_amount = 0.0

    @api.onchange('cheque_id')
    def _onchange_cheque_id(self):
        """Populate amount from selected cheque"""
        if self.cheque_id:
            self.amount = self.cheque_id.amount
            self.original_amount = self.cheque_id.amount

    @api.model
    def create(self, vals):
        # Create record in this history model
        record = super(FinanceChequeEncaisse, self).create(vals)
        
        # Update the original cheque
        if record.cheque_id and record.date_encaissement:
            # Check if already encaisse to prevent double entry race condition
            if record.cheque_id.date_encaissement:
                 raise exceptions.UserError("Ce chèque a déjà une date d'encaissement.")
                 
            # Use sudo to ensure update even if user has restricted access on datacheque write
            # Sync BOTH date_encaissement and amount
            record.cheque_id.sudo().write({
                'date_encaissement': record.date_encaissement,
                'amount': record.amount
            })
            
        return record

    def unlink(self):
        """Override unlink to revert date_encaissement and amount on original cheque."""
        for rec in self:
            if rec.cheque_id:
                # Clear the date on the original cheque AND revert amount
                rec.cheque_id.sudo().write({
                    'date_encaissement': False,
                    'amount': rec.original_amount if rec.original_amount else rec.cheque_id.amount
                })
        
        return super(FinanceChequeEncaisse, self).unlink()
