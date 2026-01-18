from odoo import models, fields, api

class FinanceSutra(models.Model):
    _name = 'finance.sutra'
    _description = 'Finance Sutra'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # -------------------------------------------------------------------------
    # SOURCE OF TRUTH (Douane / Logistique)
    # -------------------------------------------------------------------------
    douane_id = fields.Many2one(
        'logistique.entry',
        string='Dossier Douane / DUM',
        required=True,
        domain="[('dum', '!=', False)]",
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
    
    # Amounts
    amount_mad = fields.Float(related='douane_id.amount_mad', string='Montant (MAD)', readonly=True)
    customs_total = fields.Float(related='douane_id.customs_total', string='Total Douane', readonly=True)

    # -------------------------------------------------------------------------
    # FINANCE FIELDS (Editable)
    # -------------------------------------------------------------------------
    dossier_num = fields.Char(string='N° Dossier', tracking=True)
    honoraires = fields.Float(string='Honoraires', tracking=True)
    temsa = fields.Float(string='TEMSA', tracking=True)
    
    regime = fields.Selection([
        ('855', '855'),
        ('50', '50'),
        ('10', '10')
    ], string='Régime', tracking=True)
    
    facture_sutra = fields.Char(string='Facture Sutra', tracking=True)
    scan_facture = fields.Char(string='Scan Facture (Drive)', help="Lien vers le scan de la facture", tracking=True)
    
    # -------------------------------------------------------------------------
    # CHEQUE MANAGEMENT (Linked to DataCheque)
    # -------------------------------------------------------------------------
    cheque_id = fields.Many2one(
        'datacheque', 
        string='Chèque', 
        required=True, 
        domain="[('benif_id.name', 'ilike', 'SUTRA')]",
        tracking=True
    )
    
    # Related Cheque Info (Read-Only)
    date_emission = fields.Date(related='cheque_id.date_emission', string="Date d'émission", readonly=True)
    date_echeance = fields.Date(related='cheque_id.date_echeance', string="Date d'échéance", readonly=True)
    
    # Manual Cheque Info
    amount = fields.Float(string='Montant', tracking=True)
    date_encaissement = fields.Date(string="Date d'encaissement", tracking=True)
    encaisse = fields.Boolean(string='Encaissé', default=False, tracking=True)

    _sql_constraints = [
        ('douane_id_uniq', 'unique (douane_id)', 'Un dossier Sutra existe déjà pour ce dossier Douane !')
    ]

    @api.model
    def action_sync_from_douane(self):
        """
        Create Sutra records for existing Douane dossiers (Manual Sync Action).
        Filtered by existing DUM.
        """
        douane_records = self.env['logistique.entry'].search([('dum', '!=', False)])
        existing_douane_ids = self.search([]).mapped('douane_id').ids

        to_create = douane_records.filtered(
            lambda d: d.id not in existing_douane_ids
        )

        for douane in to_create:
            self.create({
                'douane_id': douane.id,
            })

        message = f"{len(to_create)} dossiers Sutra ont été synchronisés depuis la Douane."
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Synchronisation Terminée',
                'message': message,
                'sticky': False,
                'type': 'success', 
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
