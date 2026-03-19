from odoo import models, fields, api

class Cal3iyaClient(models.Model):
    _name = 'finance.benif'
    _description = 'Bénificiaires'

    name = fields.Char(string='Bénificiaire', required=True)
    days = fields.Integer(string='Jours de plus')
    type = fields.Selection([
        ('import', 'Importation'),
        ('divers', 'Divers'),
        ('bureau', 'Bureau'),
        ('annule', 'Annulé'),
        ], string='Imp/Div', required=True, store=True)

    benif_deduction = fields.Boolean(string="Autorise Paiement par Déduction", default=False)

    physical_chq_ids = fields.One2many(
        'finance.cheque.physical',
        'benif_id',
        string="Chèques Physiques"
    )

    total_credit = fields.Float(string="Total Crédit", compute="_compute_chq_totals")
    total_debit = fields.Float(string="Total Débit", compute="_compute_chq_totals")
    solde = fields.Float(string="Différence (Solde)", compute="_compute_chq_totals")

    @api.depends('physical_chq_ids.credit', 'physical_chq_ids.debit')
    def _compute_chq_totals(self):
        for rec in self:
            rec.total_credit = sum(rec.physical_chq_ids.mapped('credit'))
            rec.total_debit = sum(rec.physical_chq_ids.mapped('debit'))
            rec.solde = rec.total_credit - rec.total_debit