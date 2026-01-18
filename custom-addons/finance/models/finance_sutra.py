from odoo import models, fields, api

class FinanceSutra(models.Model):
    _name = 'finance.sutra'
    _description = 'Finance Sutra'
    _rec_name = 'bl_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # -------------------------------------------------------------------------
    # SOURCE OF TRUTH (Douane / Logistique)
    # -------------------------------------------------------------------------
    douane_id = fields.Many2one(
        'logistique.entry',
        string='Dossier Douane',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True
    )

    # -------------------------------------------------------------------------
    # READ-ONLY FIELDS (Related to Douane)
    # -------------------------------------------------------------------------
    # Global Info
    bl_number = fields.Char(related='douane_id.bl_number', string='BL Number', store=True, readonly=True)
    supplier_id = fields.Many2one(related='douane_id.supplier_id', string='Fournisseur', store=True, readonly=True)
    ste_id = fields.Many2one(related='douane_id.ste_id', string='Société', store=True, readonly=True)
    
    # Douane Info
    dum = fields.Char(related='douane_id.dum', string='N° DUM', store=True, readonly=True)
    dum_date = fields.Date(related='douane_id.dum_date', string='Date DUM', store=True, readonly=True)
    
    # Logistics Info
    container_ids = fields.One2many(related='douane_id.container_ids', string='Conteneurs', readonly=True)
    eta = fields.Date(related='douane_id.eta', string='ETA', store=True, readonly=True)
    
    # Amounts (if needed from Douane)
    amount_mad = fields.Float(related='douane_id.amount_mad', string='Montant (MAD)', readonly=True)
    customs_total = fields.Float(related='douane_id.customs_total', string='Total Douane', readonly=True)

    # -------------------------------------------------------------------------
    # FINANCE FIELDS (Editable)
    # -------------------------------------------------------------------------
    dossier_num = fields.Char(string='N° Dossier', tracking=True)
    honoraires = fields.Float(string='Honoraires', tracking=True)
    temsa = fields.Float(string='TEMSA', tracking=True)
    
    # -------------------------------------------------------------------------
    # CHEQUES MANAGEMENT
    # -------------------------------------------------------------------------
    cheque_ids = fields.One2many('finance.sutra.cheque', 'sutra_id', string='Chèques')

    _sql_constraints = [
        ('douane_id_uniq', 'unique (douane_id)', 'Un dossier Sutra existe déjà pour ce dossier Douane !')
    ]

    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.bl_number or 'N/A'} - {rec.dossier_num or 'No Dossier'}"
            result.append((rec.id, name))
        return result


class FinanceSutraCheque(models.Model):
    _name = 'finance.sutra.cheque'
    _description = 'Chèque Sutra'

    sutra_id = fields.Many2one('finance.sutra', string='Dossier Sutra', required=True, ondelete='cascade')
    
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Montant', required=True)
    type = fields.Selection([
        ('avance', 'Avance'),
        ('solde', 'Solde'),
        ('autre', 'Autre')
    ], string='Type', default='autre')
    
    cheque_number = fields.Char(string='N° Chèque')
    bank = fields.Char(string='Banque')
    
    # Beneficiary: In Logistique it's often free text or linked. 
    # Request says: "Benificiaire chosen automatically SUTRA from benif model"
    # This likely implies we might default it, but user can change? 
    # Or maybe it's just a Many2one to finance.benif with a default.
    beneficiary_id = fields.Many2one('finance.benif', string='Bénéficiaire')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Try to find 'SUTRA' beneficiary
        sutra_benif = self.env['finance.benif'].search([('name', 'ilike', 'Sutra')], limit=1)
        if sutra_benif:
            res['beneficiary_id'] = sutra_benif.id
        return res
