from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta

class DataCheque(models.Model):
    _name = 'datacheque'
    _description = 'Data chèque'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    chq = fields.Char(string='Chèque', tracking=True, size=7, required=True)
    amount = fields.Float(string='Montant', tracking=True, group_operator="sum", required=True)
    date_emission = fields.Date(string='Date d’émission', tracking=True)
    week = fields.Char(string='Semaine', compute='_compute_week', store=True)
    serie = fields.Char(string='Série de facture', tracking=True)
    date_echeance = fields.Date(string='Date d’échéance', tracking=True, compute="_compute_date_echeance", store=True)
    date_encaissement = fields.Date(string='Date d’encaissement', tracking=True)
    ste_id = fields.Many2one('finance.ste', string='Société', tracking=True, required=True)
    benif_id = fields.Many2one('finance.benif', string='Bénificiaire', tracking=True, required=True)
    perso_id = fields.Many2one('finance.perso', string='Personnes', tracking=True, required=True)
    facture = fields.Selection([
        ('m', 'M'),
        ('bureau', 'Bureau'),
        ('fact', 'F/'),
    ], string='Facture', tracking=True, required=True, default='m')
    journal = fields.Integer(string='Journal N°', required=True)
    facture_tag = fields.Html(string='Facture', compute='_compute_facture_tag', sanitize=False)
    state = fields.Selection([
        ('actif', 'Actif'),
        ('annule', 'Annulé'),
        ('bureau', 'Bureau'),
    ], string='État', default='actif', tracking=True, store=True)
    type = fields.Selection([
        ('magasinage', 'Magasinage'),
        ('surestarie', 'Surestarie'),
        ('change', 'Change'),
    ], store=True, string='Type', tracking=True)
    benif_type = fields.Selection(related="benif_id.type", store=True)
    # ------------------------------------------------------------
    # BADGE VISUEL
    # ------------------------------------------------------------
    @api.depends('facture_tag', 'facture', 'serie')
    def _compute_facture_tag(self):
        for rec in self:

            factur = rec.facture or ""  # nom de la facture

            # --- Conditions selon ta demande ---
            if factur == "fact":           # commence par 
                label = rec.serie or "F/"
                color = "#28a745"  # vert
                bg = "rgba(40,167,69,0.12)"

            elif factur == "m":                   # exactement = M
                label = "M"
                color = "#dc3545"  # rouge
                bg = "rgba(220,53,69,0.12)"

            elif factur == "bureau":             # exactement = Bureau
                label = "Bureau"
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
    # Calcul de week
    # ------------------------------------------------------------

    @staticmethod
    def french_week_number(date_obj):
        if not date_obj:
            return False

        year = date_obj.year
        first_jan = date_obj.replace(month=1, day=1)
        first_monday = first_jan - timedelta(days=first_jan.weekday())

        # Si le 1er janvier tombe après jeudi => semaine 1 commence la semaine suivante
        if first_jan.weekday() > 3:
            first_monday += timedelta(days=7)

        # Numéro de semaine selon la norme française
        delta_days = (date_obj - first_monday).days
        week = (delta_days // 7) + 1

        return f"W{week:02d}"

    # ------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------
    @api.depends('date_emission')
    def _compute_week(self):
        for rec in self:
            if rec.date_emission:
                rec.week = self.french_week_number(rec.date_emission)
            else:
                rec.week = False

    @api.depends('date_emission', 'benif_id.days', 'benif_id')
    def _compute_date_echeance(self):
        for rec in self:
            if rec.date_emission and rec.benif_id and rec.benif_id.days:
                rec.date_echeance = rec.date_emission + timedelta(days=rec.benif_id.days)
            else:
                rec.date_echeance = rec.date_emission

    # ------------------------------------------------------------
    # CONTRAINTE D’UNICITÉ
    # ------------------------------------------------------------
    @api.onchange('chq')
    def _onchange_chq_checks(self):
        for rec in self:

            # 1️⃣ Longueur exacte = 7
            if rec.chq and len(rec.chq) != 7:
                raise ValidationError("Le numéro de chèque doit contenir exactement 7 caractères.")

            # 2️⃣ Unicité
            if rec.chq and rec.ste_id:
                domain = [
                    ('chq', '=', rec.chq)
                    ('ste_id', '=', rec.ste_id.id)
                    ]

                if rec.id:
                    domain.append(('id', '!=', rec.id))

                existing = self.env['datacheque'].search(domain, limit=1)
                if existing:
                    raise ValidationError("⚠️ Ce numéro du chèque existe déja pour cette société.")

    _sql_constraints = [
        ('unique_chq_ste', 'unique(chq, ste_id)', '⚠️ Ce numéro du chèque existe déja pour cette société.')
    ]

    # ------------------------------------------------------------
    # Bureau state
    # ------------------------------------------------------------
    @api.onchange('state')
    def _onchange_state_force_facture(self):
        for rec in self:
            if rec.state == 'bureau':
                rec.facture = 'bureau'

    @api.constrains('state')
    def _check_state_force_facture(self):
        for rec in self:
            if rec.state == 'bureau' and rec.facture != 'bureau':
                rec.facture = 'bureau'

    