from odoo import models, fields, api, exceptions

class FinanceEncaissementPhysique(models.Model):
    _name = 'finance.encaissement.physique'
    _description = 'Encaissement Physique'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'physical_cheque_id'
    _order = 'create_date desc'

    ste_id = fields.Many2one('finance.ste', string='Société', required=True, tracking=True)
    benif_id = fields.Many2one('finance.benif', string='Bénéficiaire', required=True, tracking=True)
    
    physical_cheque_id = fields.Many2one(
        'finance.cheque.physical', 
        string='Chèque Physique', 
        required=True,
        domain="[('ste_id', '=', ste_id), ('benif_id', '=', benif_id), ('encours', '!=', 'encaisse')]"
    )

    amount = fields.Float(string='Montant', required=True, tracking=True)
    date_encaissement = fields.Date(string="Date d'encaissement", required=True, tracking=True, default=fields.Date.context_today)

    encaissement_line_ids = fields.One2many(
        'finance.cheque.encaisse', 
        'encaissement_physique_id', 
        string='Répartitions Encaissées', 
        readonly=True
    )

    @api.onchange('ste_id', 'benif_id')
    def _onchange_filter_reset(self):
        """Reset physical cheque selection if filters change"""
        self.physical_cheque_id = False
        self.amount = 0.0

    @api.onchange('physical_cheque_id')
    def _onchange_physical_cheque(self):
        if self.physical_cheque_id:
            self.amount = self.physical_cheque_id.amount_total

    @api.onchange('amount')
    def _onchange_amount_warning(self):
        if self.physical_cheque_id and self.amount != self.physical_cheque_id.amount_total:
            return {
                'warning': {
                    'title': "Montant différent",
                    'message': "Le montant saisi (%.2f) est différent du montant global du chèque (%.2f)." % (
                        self.amount, self.physical_cheque_id.amount_total
                    )
                }
            }

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount == 0:
                raise exceptions.ValidationError("Le montant ne peut pas être 0.")

    @api.model
    def create(self, vals):
        record = super(FinanceEncaissementPhysique, self).create(vals)
        # Create corresponding individual encaissement records
        if record.physical_cheque_id:
            for datacheque in record.physical_cheque_id.datacheque_ids:
                if not datacheque.date_encaissement and datacheque.state not in ['bureau', 'annule']:
                    self.env['finance.cheque.encaisse'].create({
                        'ste_id': datacheque.ste_id.id,
                        'benif_id': datacheque.benif_id.id,
                        'type': datacheque.type,
                        'cheque_id': datacheque.id,
                        'amount': datacheque.amount,
                        'date_encaissement': record.date_encaissement,
                        'encaissement_physique_id': record.id,
                    })
        return record

    def unlink(self):
        # Trigger unlink on children explicitly to run their python unlink logic
        for rec in self:
            rec.encaissement_line_ids.unlink()
        return super(FinanceEncaissementPhysique, self).unlink()
