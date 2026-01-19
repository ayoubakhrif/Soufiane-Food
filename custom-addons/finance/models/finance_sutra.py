from odoo import models, fields, api

class FinanceSutra(models.Model):
    _name = 'finance.sutra'
    _description = 'Finance Sutra'
    _rec_name = 'bl_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # -------------------------------------------------------------------------
    # SOURCE OF TRUTH (Douane / Logistique) - MANUAL CREATION
    # -------------------------------------------------------------------------
    douane_id = fields.Many2one(
        'logistique.entry',
        string='Dossier Douane (BL)',
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
    
    regime = fields.Selection([
        ('10', '10'),
        ('50', '50'),
        ('855', '855')
    ], string='Régime', tracking=True)
    
    facture_sutra = fields.Char(string='Facture Sutra', tracking=True)

    # Charges
    honoraires = fields.Float(string='Honoraires', tracking=True)
    temsa = fields.Float(string='TEMSA', tracking=True)
    autres = fields.Float(string='Autres charges', tracking=True)
    
    total = fields.Float(string='Total', compute='_compute_total', store=True, tracking=True)

    # -------------------------------------------------------------------------
    # CHEQUE MANAGEMENT (Linked to DataCheque)
    # -------------------------------------------------------------------------
    cheque_id = fields.Many2one(
        'datacheque',
        string='Chèque',
        domain="[('benif_id.name', 'ilike', 'SUTRA')]",
        tracking=True
    )
    
    # Read-only from Cheque
    cheque_date_emission = fields.Date(related='cheque_id.date_emission', string="Date d'émission", readonly=True)
    cheque_date_echeance = fields.Date(related='cheque_id.date_echeance', string="Date d'échéance", readonly=True)
    cheque_number = fields.Char(related='cheque_id.chq', string="N° Chèque", readonly=True)

    # Manual Fields for Processing
    date_encaissement = fields.Date(string="Date d'encaissement", tracking=True)
    amount = fields.Float(string='Montant', tracking=True)
    encaisse = fields.Boolean(string='Encaissé', default=False, tracking=True)

    _sql_constraints = [
        ('douane_id_uniq', 'unique (douane_id)', 'Un dossier Sutra existe déjà pour ce dossier Douane !')
    ]

    @api.depends('honoraires', 'temsa', 'autres')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.honoraires + rec.temsa + rec.autres

    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.bl_number or 'N/A'} - {rec.dossier_num or 'No Dossier'}"
            result.append((rec.id, name))
        return result
