from odoo import models, fields, api

class LogistiqueDossierCheque(models.Model):
    _name = 'logistique.dossier.cheque'
    _description = 'Chèque Dossier Logistique'

    dossier_id = fields.Many2one('logistique.dossier', string='Dossier', required=True, ondelete='cascade')
    cheque_serie = fields.Char(string='Série Chèque', required=True, size=7)
    date = fields.Date(string='Date')
    beneficiary_id = fields.Many2one('logistique.shipping', string='Bénéficiaire')
    amount = fields.Float(string='Montant', required=True)
    ste_id = fields.Many2one('logistique.ste', string='Société', required=True)
    type = fields.Selection([
        ('thc', 'THC'),
        ('magasinage', 'Magasinage'),
        ('fret', 'FRET'),
        ('surestarie', 'Surestarie'),
    ], string='Type')
    surestarie_amount = fields.Float(
        string="Surestarie",
        compute="_compute_charges",
        store=True
    )
    thc_amount = fields.Float(
        string="THC",
        compute="_compute_charges",
        store=True
    )
    magasinage_amount = fields.Float(
        string="Magasinage",
        compute="_compute_charges",
        store=True
    )

    @api.depends('cheque_ids.amount', 'cheque_ids.type')
    def _compute_charges(self):
        for rec in self:
            rec.surestarie_amount = sum(
                c.amount for c in rec.cheque_ids if c.type == 'surestarie'
            )
            rec.thc_amount = sum(
                c.amount for c in rec.cheque_ids if c.type == 'thc'
            )
            rec.magasinage_amount = sum(
                c.amount for c in rec.cheque_ids if c.type == 'magasinage'
            )
