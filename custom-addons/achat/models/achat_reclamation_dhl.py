from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AchatReclamationDHL(models.Model):
    _name = 'achat.reclamation.dhl'
    _description = 'Réclamation DHL'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'bl_number'
    _order = 'create_date desc'

    # =========================
    # Reference dossier
    # =========================
    dossier_id = fields.Many2one(
        'logistique.dossier',
        string='Dossier / BL',
        required=True,
        tracking=True
    )

    bl_number = fields.Char(
        string='BL',
        related='dossier_id.name',
        store=True,
        readonly=True
    )

    # =========================
    # Infos auto-remplies
    # =========================
    supplier_id = fields.Many2one(
        'logistique.supplier',
        related='dossier_id.supplier_id',
        readonly=True
    )

    ste_id = fields.Many2one(
        'logistique.ste',
        related='dossier_id.ste_id',
        readonly=True
    )

    eta = fields.Date(
        related='dossier_id.eta',
        readonly=True
    )

    # =========================
    # DHL reclamation data
    # =========================
    dhl_number = fields.Char(string='Numéro DHL', required=True, tracking=True)
    eta_dhl = fields.Date(string='Date DHL', required=True, tracking=True)

    reason = fields.Char(string='Motif de la réclamation')
    note = fields.Text(string='Commentaire')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmée'),
        ('cancelled', 'Annulée'),
    ], default='draft', tracking=True)

    # =========================
    # Actions
    # =========================
    def action_confirm(self):
        for rec in self:
            if not rec.dossier_id:
                raise ValidationError("Aucun dossier lié.")

            # 🔁 Mise à jour directe du dossier / entry
            rec.dossier_id.write({
                'dhl_number': rec.dhl_number,
                'eta_dhl': rec.eta_dhl,
            })

            rec.state = 'confirmed'

    def action_cancel(self):
        self.write({'state': 'cancelled'})
