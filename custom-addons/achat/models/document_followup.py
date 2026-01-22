from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class AchatDocumentFollowup(models.Model):
    _name = 'achat.document.followup'
    _description = 'Suivi des Documents Achat'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'bl_id'
    _order = 'create_date desc'

    # 1. Linked Document
    bl_id = fields.Many2one(
        'logistique.entry',
        string='Dossier / BL',
        required=True,
        domain="[('bl_number', '!=', False)]",
        tracking=True
    )

    # 2. Auto-filled info (Read-only)
    supplier_id = fields.Many2one(related='bl_id.supplier_id', string='Supplier', readonly=True, store=True)
    company_id = fields.Many2one(related='bl_id.ste_id', string='Société', readonly=True, store=True)
    invoice_number = fields.Char(related='bl_id.invoice_number', string='Invoice Number', readonly=True, store=True)

    # 3. Issue Details
    document_type = fields.Selection([
        ('invoice', 'Commercial Invoice'),
        ('packing', 'Packing List'),
        ('bl', 'Bill of Lading'),
        ('fito', 'Fito Sanitaire'),
        ('origin', 'Certificate of Origin'),
        ('health', 'Health Certificate'),
        ('fumigation', 'Fumigation Certificate'),
        ('other', 'Autre'),
    ], string='Document avec problème', required=True, tracking=True)

    comment = fields.Text(string='Commentaire / Problème', required=True, tracking=True)

    # 4. Workflow State
    state = fields.Selection([
        ('initial', 'Initial'),
        ('sent', 'Envoyé au Fournisseur'),
        ('confirmed', 'Confirmé'),
    ], string='Statut', default='initial', required=True, tracking=True, copy=False)

    # 5. Dates Tracking
    # create_date is automatically handled by Odoo
    
    date_sent = fields.Date(
        string='Date Envoi Fournisseur',
        tracking=True,
        help="Date à laquelle la demande de correction a été envoyée."
    )
    
    date_confirmed = fields.Date(
        string='Date Confirmation',
        readonly=True,
        tracking=True,
        copy=False,
        help="Date à laquelle la correction a été confirmée."
    )

    # ==========================
    # Workflow Methods
    # ==========================


    def action_confirm(self):
        """Sent -> Confirmed"""
        for rec in self:
            if not self.env.user.has_group('achat.group_purchase_manager'):
                 raise ValidationError(_("Seul le responsable achat peut confirmer."))
            rec.write({
                'state': 'confirmed',
                'date_confirmed': fields.Date.context_today(self)
            })

    def action_send(self):
        """Initial -> Sent"""
        for rec in self:
            if not self.env.user.has_group('achat.group_purchase_manager'):
                 raise ValidationError(_("Seul le responsable achat peut envoyer au fournisseur."))
            if not rec.date_sent:
                raise ValidationError(_("Vous devez renseigner la 'Date Envoi Fournisseur' avant de changer l'état."))
            rec.state = 'sent'

    # ==========================
    # Constraints / Logic
    # ==========================
    
    @api.onchange('state')
    def _on_state_change(self):
        # Prevent manual changes to date_confirmed via UI tricks, 
        # though readonly=True protects it in view.
        pass
