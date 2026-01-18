from odoo import models, fields, api

class FinanceMarglory(models.Model):
    _name = 'finance.marglory'
    _description = 'Finance Marglory'
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
    cheque_ids = fields.One2many('finance.marglory.cheque', 'marglory_id', string='Chèques')

    _sql_constraints = [
        ('douane_id_uniq', 'unique (douane_id)', 'Un dossier Marglory existe déjà pour ce dossier Douane !')
    ]

    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.bl_number or 'N/A'} - {rec.dossier_num or 'No Dossier'}"
            result.append((rec.id, name))
        return result

    @api.model
    def action_sync_from_douane(self):
        """
        Create Marglory records for any Douane dossiers that don't have one yet.
        Safe to run multiple times.
        """
        douane_records = self.env['logistique.entry'].search([])
        existing_douane_ids = self.search([]).mapped('douane_id').ids

        to_create = douane_records.filtered(
            lambda d: d.id not in existing_douane_ids
        )

        for douane in to_create:
            self.create({
                'douane_id': douane.id,
            })

        message = f"{len(to_create)} dossiers Marglory ont été synchronisés depuis la Douane."
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


class FinanceMargloryCheque(models.Model):
    _name = 'finance.marglory.cheque'
    _description = 'Chèque Marglory'

    marglory_id = fields.Many2one('finance.marglory', string='Dossier Marglory', required=True, ondelete='cascade')
    
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Montant', required=True)
    type = fields.Selection([
        ('avance', 'Avance'),
        ('solde', 'Solde'),
        ('autre', 'Autre')
    ], string='Type', default='autre')
    
    cheque_number = fields.Char(string='N° Chèque')
    bank = fields.Char(string='Banque')
    
    beneficiary_id = fields.Many2one('finance.benif', string='Bénéficiaire')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Try to find 'Marglory' beneficiary
        marglory_benif = self.env['finance.benif'].search([('name', 'ilike', 'Marglory')], limit=1)
        if marglory_benif:
            res['beneficiary_id'] = marglory_benif.id
        return res
