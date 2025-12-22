from odoo import models, fields, api, exceptions

class FinanceChequeEncaisse(models.Model):
    _name = 'finance.cheque.encaisse'
    _description = 'Chèque Encaissé'
    _rec_name = 'cheque_id'
    _order = 'create_date desc'

    ste_id = fields.Many2one('finance.ste', string='Société', required=True)
    date_emission = fields.Date(string='Date d’émission', required=True)
    
    cheque_id = fields.Many2one(
        'datacheque', 
        string='Chèque', 
        required=True,
        domain="[('ste_id', '=', ste_id), ('date_emission', '=', date_emission), ('date_encaissement', '=', False)]"
    )
    
    # Readonly related fields for display
    journal = fields.Integer(related='cheque_id.journal', string='Journal N°', readonly=True)
    benif_id = fields.Many2one(related='cheque_id.benif_id', string='Bénéficiaire', readonly=True)
    amount = fields.Float(related='cheque_id.amount', string='Montant', readonly=True)
    
    date_encaissement = fields.Date(string='Date d’encaissement', required=True, default=fields.Date.context_today)

    @api.onchange('ste_id', 'date_emission')
    def _onchange_filter_reset(self):
        """Reset cheque selection if filters change"""
        self.cheque_id = False

    @api.model
    def create(self, vals):
        # Create record in this history model
        record = super(FinanceChequeEncaisse, self).create(vals)
        
        # Update the original cheque
        if record.cheque_id and record.date_encaissement:
            # Check if already encaisse to prevent double entry race condition
            if record.cheque_id.date_encaissement:
                 raise exceptions.UserError("Ce chèque a déjà une date d'encaissement.")
                 
            # Use sudo to ensure update even if user has restricted access on datacheque write (though unlikely for finance users)
            record.cheque_id.sudo().write({
                'date_encaissement': record.date_encaissement
            })
            
        return record
