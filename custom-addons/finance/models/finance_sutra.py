from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re

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
    regime = fields.Selection([
        ('10', '10'),
        ('50', '50'),
        ('855', '855')
    ], string='Régime', tracking=True)
    
    facture_sutra = fields.Char(string='Facture Sutra', tracking=True)
    scan_sutra = fields.Char(string='Scan Facture (Drive)', help="Poser le lien vers le scan de la facture")

    # Charges
    honoraires = fields.Float(string='Honoraires', tracking=True)
    temsa = fields.Float(string='TEMSA', tracking=True)
    autres = fields.Float(string='Autres charges', tracking=True)
    tva = fields.Float(string='TVA', compute='_compute_tva', tracking=True)
    
    total = fields.Float(string='Total', compute='_compute_total', store=True, tracking=True)

    # -------------------------------------------------------------------------
    # CHEQUE MANAGEMENT (Linked to DataCheque via Payment)
    # -------------------------------------------------------------------------
    payment_id = fields.Many2one('finance.sutra.payment', string='Paiement', readonly=True, tracking=True)
    
    cheque_id = fields.Many2one(
        related='payment_id.cheque_id',
        string='Chèque',
        readonly=True,
        store=True
    )
    
    # Read-only from Cheque
    cheque_date_emission = fields.Date(related='cheque_id.date_emission', string="Date d'émission", readonly=True)
    cheque_date_echeance = fields.Date(related='cheque_id.date_echeance', string="Date d'échéance", readonly=True)
    cheque_number = fields.Char(related='cheque_id.chq', string="N° Chèque", readonly=True)
    
    # Encaissement Status (from DataCheque)
    is_encaisse = fields.Boolean(string='Encaissé', compute='_compute_is_encaisse', store=True)

    @api.depends('cheque_id.encours')
    def _compute_is_encaisse(self):
        for rec in self:
            rec.is_encaisse = (rec.cheque_id.encours == 'encaisse')

    scan_sutra_url = fields.Char(
        string="Scan Facture",
        compute="_compute_scan_url"
    )
    container_names = fields.Char(
        string="Conteneurs",
        compute="_compute_container_names",
        store=True
    )
    week = fields.Char(
        string="Semaine",
        help="Format : W01 à W52 (ex: W12)",
        store=True
    )
    @api.depends('scan_sutra')
    def _compute_scan_url(self):
        for rec in self:
            if rec.scan_sutra:
                if rec.scan_sutra.startswith('http'):
                    rec.scan_sutra_url = rec.scan_sutra
                else:
                    rec.scan_sutra_url = 'https://' + rec.scan_sutra
            else:
                rec.scan_sutra_url = False

    _sql_constraints = [
        ('douane_id_uniq', 'unique (douane_id)', 'Un dossier Sutra existe déjà pour ce dossier Douane !')
    ]

    @api.depends('honoraires', 'temsa', 'autres')
    def _compute_tva(self):
        for rec in self:
            rec.tva = (rec.honoraires + rec.temsa + rec.autres)*0.2

    @api.depends('honoraires', 'temsa', 'autres', 'tva')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.honoraires + rec.temsa + rec.autres + rec.tva

    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.bl_number or 'N/A'} - {rec.facture_sutra or 'No Facture'}"
            result.append((rec.id, name))
        return result
    @api.depends('douane_id.container_ids.name')
    def _compute_container_names(self):
        for rec in self:
            rec.container_names = ', '.join(
                rec.douane_id.container_ids.mapped('name')
            )

    @api.constrains('scan_sutra')
    def _check_scan_sutra_required(self):
        for rec in self:
            if not rec.scan_sutra:
                raise ValidationError(
                    "Merci de scanner la facture avant d'enregistrer."
                )
    @api.constrains('week')
    def _check_week_format(self):
        for rec in self:
            if rec.week and not re.match(r'^W(0[1-9]|[1-4][0-9]|5[0-2])$', rec.week):
                raise ValidationError(
                    "Format de semaine invalide.\n"
                    "Utilisez : W01 à W52 (ex: W12)"
                )

    @api.constrains('payment_id')
    def _check_single_payment(self):
        for rec in self:
            if rec.payment_id:
                other = self.search([
                    ('id', '!=', rec.id),
                    ('douane_id', '=', rec.douane_id.id),
                    ('payment_id', '!=', False),
                ], limit=1)
                if other:
                    raise ValidationError(
                        "Cette facture Sutra est déjà payée par un autre chq."
                    )

    @api.constrains('regime', 'ste_id')
    def _check_regime_855_only_sn(self):
        for rec in self:
            if rec.regime == '855' and rec.ste_id:
                if rec.ste_id.name != 'SN':
                    raise ValidationError(
                        "Le régime 855 est autorisé uniquement pour la société SN."
                    )