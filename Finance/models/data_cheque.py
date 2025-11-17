from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class DataCheque(models.Model):
    _name = 'datacheque'
    _description = 'Data chèque'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    chq = fields.Char(string='Chèque', required=True, tracking=True, size=7)
    amount = fields.Float(string='Montant', required=True, tracking=True, group_operator="sum")
    date_emission = fields.Date(string='Date d’émission', tracking=True)
    week = fields.Char(string='Semaine', compute='_compute_week', store=True)
    date_echeance = fields.Date(string='Date d’échéance', tracking=True)
    date_encaissement = fields.Date(string='Date d’encaissement', tracking=True)
    ste_id = fields.Many2one('finance.ste', string='Société', tracking=True)
    benif_id = fields.Many2one('finance.benif', string='Bénificiaire', tracking=True)
    perso_id = fields.Many2one('finance.perso', string='Personnes', tracking=True)
    facture = fields.Selection([
        ('m', 'M'),
        ('bureau', 'Bureau'),
        ('facture', 'F/'),
    ], string='Facture', tracking=True, required=True)
    journal = fields.Char(string='Journal N°', required=True)
    facture_tag = fields.Html(string='Facture', compute='_compute_facture_tag', sanitize=False)
    # ------------------------------------------------------------
    # BADGE VISUEL
    # ------------------------------------------------------------
    @api.depends('facture_tag', 'facture')
    def _compute_facture_tag(self):
        for rec in self:

            factur = rec.facture or ""  # nom de la facture

            # --- Conditions selon ta demande ---
            if factur.startswith("F/"):           # commence par F/
                label = factur
                color = "#28a745"  # vert
                bg = "rgba(40,167,69,0.12)"

            elif factur == "M":                   # exactement = M
                label = factur
                color = "#dc3545"  # rouge
                bg = "rgba(220,53,69,0.12)"

            elif factur == "Bureau":             # exactement = Bureau
                label = factur
                color = "#007bff"  # bleu
                bg = "rgba(0,123,255,0.12)"

            else:                                  # tout le reste
                label = factur
                color = "#6c757d"  # gris
                bg = "rgba(108,117,125,0.12)"

            rec.facture_tag = (
                f"<span style='display:inline-block;padding:2px 8px;border-radius:12px;"
                f"font-weight:600;background:{bg};color:{color};'>"
                f"{label}"
                f"</span>"
            )

    # ------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------
    @api.depends('date_emission')
    def _compute_week(self):
        for record in self:
            if record.date_emission:
                record.week = record.date_emission.strftime("%Y-W%W")
            else:
                record.week = False
    # ------------------------------------------------------------
    # CONTRAINTE D’UNICITÉ
    # ------------------------------------------------------------
    @api.onchange('chq')
    def _onchange_chq_unique(self):
        for rec in self:
            if rec.chq:
                domain = [('chq', '=', rec.chq)]

                # 🔥 si le record existe déjà en base
                if rec.id and isinstance(rec.id, int):
                    domain.append(('id', '!=', rec.id))

                # 🔍 Recherche
                existing = self.env['datacheque'].search(domain, limit=1)

                if existing:
                    raise ValidationError("⚠️ Ce numéro de chèque existe déjà. Il doit être unique.")
