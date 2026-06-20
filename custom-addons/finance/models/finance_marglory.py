from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re

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
        ondelete='cascade',
        tracking=True,
        index=True
    )

    # -------------------------------------------------------------------------
    # READ-ONLY FIELDS (Related to Douane)
    # -------------------------------------------------------------------------
    bl_number = fields.Char(related='douane_id.bl_number', string='BL Number', store=True, readonly=True)
    supplier_id = fields.Many2one(related='douane_id.supplier_id', string='Fournisseur', store=True, readonly=True)
    ste_id = fields.Many2one(related='douane_id.ste_id', string='Société', store=True, readonly=True)
    
    dum = fields.Char(related='douane_id.dum', string='N° DUM', store=True, readonly=True)
    eta = fields.Date(related='douane_id.eta', string='ETA', store=True, readonly=True)
    
    container_ids = fields.One2many(related='douane_id.container_ids', string='Conteneurs', readonly=True)

    # -------------------------------------------------------------------------
    # FINANCE FIELDS (Editable)
    # -------------------------------------------------------------------------
    dossier_reglement = fields.Char(
        string="Réglement N°",
        tracking=True
    )
    journal = fields.Integer(string='Journal', tracking=True)
    type = fields.Selection([
        ('THC', 'THC'),
        ('FRET', 'FRET'),
        ('ASSURANCE', 'Assurance')
    ], string="Type", required=True, default='THC', tracking=True)
    
    facture_marglory = fields.Char(string='Facture Marglory', tracking=True, required=True)
    scan_marglory = fields.Char(string='Scan Facture (Drive)', required=True, tracking=True)
    
    amount = fields.Float(string='Montant Total', required=True, tracking=True)

    # -------------------------------------------------------------------------
    # PAYMENT LINK
    # -------------------------------------------------------------------------
    payment_id = fields.Many2one(
        'finance.marglory.payment', 
        string='Paiement', 
        readonly=True, 
        tracking=True,
        ondelete='set null'
    )

    # -------------------------------------------------------------------------
    # CHEQUE INFO (Read-only from Payment)
    # -------------------------------------------------------------------------
    cheque_id = fields.Many2one(related='payment_id.physical_cheque_id', string='Chèque', store=False, readonly=True)
    cheque_number = fields.Char(related='cheque_id.name', string='N° Chèque', readonly=True)
    cheque_date_emission = fields.Date(related='cheque_id.date_emission', string="Date d'émission", readonly=True)
    cheque_date_echeance = fields.Date(related='cheque_id.date_echeance', string="Date d'échéance", readonly=True)
    cheque_date_limite = fields.Date(related='cheque_id.date_limite', string="D. limite", readonly=True)
    cheque_amount = fields.Float(related='cheque_id.amount_total', string="Montant chq", readonly=True)
    cheque_encours = fields.Selection(related='cheque_id.encours', string="D. Encaissement", readonly=True)
    
    fac_comm = fields.Char(related='douane_id.invoice_number', string="Fac comm", readonly=True)
    article_id = fields.Many2one(related='douane_id.achat_article_id', string="Article", readonly=True)
    
    is_encaisse = fields.Boolean(string='Encaissé', compute='_compute_is_encaisse', store=True)

    # -------------------------------------------------------------------------
    # COMPUTED FIELDS
    # -------------------------------------------------------------------------
    scan_marglory_url = fields.Char(string="Lien Scan", compute="_compute_scan_url")
    container_names = fields.Char(string="Conteneurs", compute="_compute_container_names", store=True)

    _sql_constraints = [
        ('douane_id_type_uniq', 'unique (douane_id, type)', 'Un dossier Marglory de ce type existe déjà pour ce dossier Douane !')
    ]

    @api.depends('cheque_id.encours')
    def _compute_is_encaisse(self):
        for rec in self:
            rec.is_encaisse = (rec.cheque_id.encours == 'encaisse')

    @api.depends('scan_marglory')
    def _compute_scan_url(self):
        for rec in self:
            if rec.scan_marglory:
                if rec.scan_marglory.startswith('http'):
                    rec.scan_marglory_url = rec.scan_marglory
                else:
                    rec.scan_marglory_url = 'https://' + rec.scan_marglory
            else:
                rec.scan_marglory_url = False

    @api.depends('douane_id.container_ids.name')
    def _compute_container_names(self):
        for rec in self:
            rec.container_names = ', '.join(rec.douane_id.container_ids.mapped('name'))

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('scan_marglory')
    def _check_scan_marglory_required(self):
        for rec in self:
            if not rec.scan_marglory or not rec.scan_marglory.strip():
                raise ValidationError("Le lien du scan est obligatoire. Merci de le renseigner.")
    @api.constrains('amount')
    def _check_positive_amount(self):
        for rec in self:
            if rec.amount < 0:
                raise ValidationError("Le montant doit être positif.")

    @api.constrains('payment_id')
    def _check_single_payment(self):
        for rec in self:
            if rec.payment_id:
                # Ensure no other invoice links to the same payment if logic dictated 1-to-1, 
                # but requirement is 1 cheque -> many invoices, 1 invoice -> 1 cheque.
                # The Many2one field already enforces 1 invoice -> 1 cheque.
                # We just need to ensure we don't accidentally over-write or link if typically restricted?
                # Actually, Many2one is enough structure-wise.
                # But let's check if there's any weird state.
                pass

    def write(self, vals):
        # Backend protection: Prevent changing payment if already paid
        if 'payment_id' in vals:
            for rec in self:
                if rec.payment_id and vals['payment_id'] != rec.payment_id.id:
                    # Allow removing payment (setting to False) if needed? 
                    # Or strictly block any change if already paid?
                    # User said: "strictly block linking an invoice that is already paid"
                    # Usually means if I have a payment, I shouldn't change it easily.
                    # But if I cancel payment, I should be able to unlink.
                    # Let's assess: if payment_id is set, and we try to change it to another ID:
                    if vals['payment_id']:
                         raise ValidationError("Impossible de modifier le paiement d'une facture déjà payée. Veuillez d'abord annuler le paiement existant.")
        return super(FinanceMarglory, self).write(vals)

    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.bl_number or 'N/A'} - {rec.facture_marglory or 'No Facture'}"
            result.append((rec.id, name))
        return result
