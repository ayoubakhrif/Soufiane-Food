from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

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
    benif_id = fields.Many2one('finance.benif', string='Bénificiaire', tracking=True)
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
    chq_pdf_url = fields.Char("Lien PDF CHQ", readonly=True)
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
    # CONTRAINTES
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
                    ('chq', '=', rec.chq),
                    ('ste_id', '=', rec.ste_id.id),
                ]

                if rec.id:
                    domain.append(('id', '!=', rec.id))

                existing = self.env['datacheque'].search(domain, limit=1)
                if existing:
                    raise ValidationError("⚠️ Ce numéro du chèque existe déja pour cette société.")

    _sql_constraints = [
        ('unique_chq_ste', 'unique(chq, ste_id)', '⚠️ Ce numéro du chèque existe déja pour cette société.')
    ]

    @api.constrains('state')
    def _check_state_annule(self):
        for rec in self:
            if rec.state == 'annule':

                annule_perso = rec._get_annule_perso()
                if annule_perso:
                    rec.perso_id = annule_perso

                rec.date_echeance = False
                rec.benif_id = False
                rec.serie = "Annulé"

    # ------------------------------------------------------------
    # Bureau state
    # ------------------------------------------------------------
    def _get_annule_perso(self):
        return self.env['finance.perso'].search([('name', '=', 'Annulé')], limit=1)
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

    # ------------------------------------------------------------
    # if state == Annulé
    # ------------------------------------------------------------
    @api.onchange('state')
    def _onchange_state_annule(self):
        for rec in self:
            if rec.state == 'annule':

                annule_perso = rec._get_annule_perso()
                if annule_perso:
                    rec.perso_id = annule_perso

                rec.date_echeance = False
                rec.benif_id = False
                rec.serie = "Annulé"
    # ------------------------------------------------------------
    # RECHERCHE DE CHQ
    # ------------------------------------------------------------
    # Chemin vers le JSON
    def _get_drive_credentials_path(self):
        return "/srv/google_credentials/odoo_drive_service.json"

    # 1) Connexion API Google Drive
    def _get_drive_service(self):
        creds_path = self._get_drive_credentials_path()
        scopes = ['https://www.googleapis.com/auth/drive.readonly']
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
        return build('drive', 'v3', credentials=creds)

    # 2) Recherche dossier exact
    def _find_folder_exact(self, service, folder_name, parent_id):
        query = (
            "mimeType='application/vnd.google-apps.folder' "
            f"and name='{folder_name}' "
            f"and '{parent_id}' in parents and trashed=false"
        )
        res = service.files().list(q=query, fields="files(id, name)").execute()
        f = res.get("files", [])
        return f[0]["id"] if f else None

    # 3) Trouver sous-dossier contenant le numéro du chèque
    def _find_folder_contains(self, service, keyword, parent_id):
        query = (
            "mimeType='application/vnd.google-apps.folder' "
            f"and name contains '{keyword}' "
            f"and '{parent_id}' in parents and trashed=false"
        )
        res = service.files().list(q=query, fields="files(id, name)").execute()
        f = res.get("files", [])
        return f[0]["id"] if f else None

    # 4) Recherche PDF contenant CHQ
    def _find_pdf_chq(self, service, parent_id):
        query = (
            "mimeType='application/pdf' "
            "and name contains 'CHQ' "
            f"and '{parent_id}' in parents "
            "and trashed=false"
        )
        res = service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
        f = res.get("files", [])
        return f[0]["webViewLink"] if f else None

    # 5) Fonction principale : trouver URL du CHQ
    def _get_chq_pdf_url(self, ste_name, cheque_number):
        icp = self.env["ir.config_parameter"].sudo()
        root_id = icp.get_param("finance.drive.root_folder_id")

        if not root_id or not ste_name or not cheque_number:
            return False

        service = self._get_drive_service()

        # Étape 1 : dossier société
        ste_folder_id = self._find_folder_exact(service, ste_name, root_id)
        if not ste_folder_id:
            return False

        # Étape 2 : sous-dossier contenant numéro chèque
        sub_folder_id = self._find_folder_contains(service, cheque_number, ste_folder_id)
        if not sub_folder_id:
            return False

        # Étape 3 : PDF contenant "CHQ"
        url = self._find_pdf_chq(service, sub_folder_id)
        return url or False

    # 6) Mettre à jour automatiquement l’URL
    def _sync_pdf_url(self):
        for rec in self:
            if rec.ste_id and rec.chq:
                rec.chq_pdf_url = rec._get_chq_pdf_url(rec.ste_id.name, rec.chq)
            else:
                rec.chq_pdf_url = False

    # 7) Override create/write
    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._sync_pdf_url()
        return rec

    def write(self, vals):
        res = super().write(vals)
        if "chq" in vals or "ste_id" in vals:
            self._sync_pdf_url()
        return res

    # 8) Bouton ouverture PDF
    def action_open_pdf_chq(self):
        self.ensure_one()
        if not self.chq_pdf_url:
            raise UserError("Aucun PDF CHQ trouvé sur Drive.")
        return {
            "type": "ir.actions.act_url",
            "url": self.chq_pdf_url,
            "target": "new",
        }