from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

class DataCheque(models.Model):
    _name = 'datacheque'
    _description = 'Data chèque'
    _description = 'Data chèque'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'chq'

    chq = fields.Char(string='Chèque', tracking=True, size=7, required=True)
    
    is_manager = fields.Boolean(compute='_compute_is_manager', string="Is Manager")

    def _compute_is_manager(self):
        for rec in self:
            rec.is_manager = self.env.user.has_group('finance.group_finance_user')
    amount = fields.Float(string='Montant', tracking=True, group_operator="sum", required=True)
    date_operation = fields.Date(string='Date Operation', default=fields.Date.context_today)
    date_payment = fields.Date(string='Date Paiement')
    cheque_count = fields.Integer(string='Nombre chèques', default=1, store=True)
    date_emission = fields.Date(string='Date d’émission', tracking=True, required=True)
    week = fields.Char(string='Semaine', compute='_compute_week', store=True)
    serie = fields.Char(string='Série de facture', tracking=True)
    date_echeance = fields.Date(string='Date d’échéance', tracking=True, compute="_compute_date_echeance", store=True, required=True)
    date_encaissement = fields.Date(string='Date d’encaissement', tracking=True)
    ste_id = fields.Many2one('finance.ste', string='Société', tracking=True, required=True)
    benif_id = fields.Many2one('finance.benif', string='Bénificiaire', tracking=True, required=True)
    perso_id = fields.Many2one('finance.perso', string='Personnes', tracking=True, required=True)
    facture = fields.Selection([
        ('m', 'M'),
        ('bureau', 'Bureau'),
        ('fact', 'F/'),
    ], string='Facture', tracking=True, required=True, default='m')
    journal = fields.Char(string='Journal N°', required=True)
    facture_tag = fields.Html(string='Facture', compute='_compute_facture_tag', sanitize=False, optional=True)
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
    dem_pdf_url = fields.Char("Lien PDF DEM", readonly=True)
    doc_pdf_url = fields.Char("Lien PDF DOC", readonly=True)
    chq_exist = fields.Selection([
        ('chq_exists', 'Existe'),
        ('chq_not_exists', 'Manquant'),
    ], readonly=True, optional=True)
    dem_exist = fields.Selection([
        ('dem_exists', 'Existe'),
        ('dem_not_exists', 'Manquant'),
    ], readonly=True, optional=True)
    doc_exist = fields.Selection([
        ('doc_exists', 'Existe'),
        ('doc_not_exists', 'Manquant'),
    ], readonly=True, optional=True)
    existing_tag = fields.Html(string='Présence CHQ', compute='_compute_existance_tag', sanitize=False, optional=True, store=True)
    existing_dem_tag = fields.Html(string='Présence DEM', compute='_compute_existance_dem_tag', sanitize=False, optional=True, store=True)
    existing_doc_tag = fields.Html(string='Présence DOC', compute='_compute_existance_doc_tag', sanitize=False, optional=True, store=True)
    talon_id = fields.Many2one('finance.talon', string='Talon', tracking=True, domain="[('ste_id', '=', ste_id)]")
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

    @api.depends('existing_tag', 'chq_exist', 'chq_pdf_url')
    def _compute_existance_tag(self):
        for rec in self:

            existance = rec.chq_exist or ""  # présence de chèque

            # --- Conditions selon ta demande ---
            if existance == "chq_exists":           # commence par 
                label = "CHQ Existe"
                color = "#28a745"  # vert
                bg = "rgba(40,167,69,0.12)"

            else:                   # exactement = M
                label = "CHQ Manquant"
                color = "#dc3545"  # rouge
                bg = "rgba(220,53,69,0.12)"

            rec.existing_tag = (
                f"<span style='display:inline-block;padding:2px 8px;border-radius:12px;"
                f"font-weight:600;background:{bg};color:{color};'>"
                f"{label}"
                f"</span>"
            )

    @api.depends('dem_exist', 'dem_pdf_url', 'existing_dem_tag')
    def _compute_existance_dem_tag(self):
        for rec in self:

            existance = rec.dem_exist or ""  # présence de chèque

            # --- Conditions selon ta demande ---
            if existance == "dem_exists":           # commence par 
                label = "DEM Existe"
                color = "#28a745"  # vert
                bg = "rgba(40,167,69,0.12)"

            else:                   # exactement = M
                label = "DEM Manquant"
                color = "#dc3545"  # rouge
                bg = "rgba(220,53,69,0.12)"

            rec.existing_dem_tag = (
                f"<span style='display:inline-block;padding:2px 8px;border-radius:12px;"
                f"font-weight:600;background:{bg};color:{color};'>"
                f"{label}"
                f"</span>"
            )

    @api.depends('doc_exist', 'doc_pdf_url', 'existing_doc_tag')
    def _compute_existance_doc_tag(self):
        for rec in self:

            existance = rec.doc_exist or ""  # présence de chèque

            # --- Conditions selon ta demande ---
            if existance == "doc_exists":           # commence par 
                label = "DOC Existe"
                color = "#28a745"  # vert
                bg = "rgba(40,167,69,0.12)"

            else:                   # exactement = M
                label = "DOC Manquant"
                color = "#dc3545"  # rouge
                bg = "rgba(220,53,69,0.12)"

            rec.existing_doc_tag = (
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

    @api.constrains('date_emission')
    def _check_date_emission_not_in_future(self):
        """Empêche de saisir une date d’émission dans le futur."""
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.date_emission and rec.date_emission > today:
                raise ValidationError("La date d’émission ne peut pas être supérieure à la date d’aujourd’hui.")

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

    # -------------------------------------------------------------------
    # Calculate TALON
    # -------------------------------------------------------------------
    def _find_talon_logic(self):
        self.ensure_one()
        if not self.chq or not self.ste_id:
            return False
            
        if not self.chq.isdigit():
            return False

        chq_num = int(self.chq)

        talons = self.env['finance.talon'].search([
            ('ste_id', '=', self.ste_id.id),
            ('num_chq', '>', 0),
            ('name', '!=', False),
        ])

        for talon in talons:
            if not talon.name or not talon.name.isdigit():
                continue

            start = int(talon.name)
            end = start + talon.num_chq - 1

            if start <= chq_num <= end:
                return talon
        return False

    @api.onchange('chq', 'ste_id')
    def _onchange_find_talon(self):
        """Détecte automatiquement le talon en fonction de la société + numéro de chèque."""
        for rec in self:
            rec.talon_id = rec._find_talon_logic()

    # -------------------------------------------------------------------
    # CRON : Update talons
    # -------------------------------------------------------------------
    @api.model
    def cron_find_all_talons(self):
        """Met à jour les talons pour tous les chèques (3 fois seulement)."""
        # On peut optimiser en ne prenant que ceux sans talon, 
        # mais la demande semble générale.
        records = self.search([])
        for rec in records:
            found = rec._find_talon_logic()
            if found and rec.talon_id != found:
                rec.talon_id = found

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
    def _find_pdf_by_keyword(self, service, parent_id, keyword):
        """Cherche un PDF contenant un mot-clé (CHQ / DEM / DOC) dans le même dossier."""
        query = (
            "mimeType='application/pdf' "
            f"and name contains '{keyword}' "
            f"and '{parent_id}' in parents "
            "and trashed=false"
        )
        res = service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
        f = res.get("files", [])
        return f[0]["webViewLink"] if f else None

    # 5) Fonction principale : trouver URL du CHQ
    def _get_pdf_url(self, keyword):
        """Retourne l'URL d'un PDF selon un mot-clé : CHQ, DEM ou DOC."""
        icp = self.env["ir.config_parameter"].sudo()
        root_id = icp.get_param("finance.drive.root_folder_id")

        if not root_id or not self.ste_id or not self.chq:
            return False

        service = self._get_drive_service()

        # Dossier Société
        ste_folder_id = self._find_folder_exact(service, self.ste_id.name, root_id)
        if not ste_folder_id:
            return False

        # Sous-dossier contenant le numéro de CHQ
        sub_folder_id = self._find_folder_contains(service, self.chq, ste_folder_id)
        if not sub_folder_id:
            return False

        # Chercher un PDF dans ce sous-dossier contenant le mot-clé
        return self._find_pdf_by_keyword(service, sub_folder_id, keyword)


    # 6) Mettre à jour automatiquement l’URL
    def _sync_pdf_url(self):
        """Met à jour les PDF CHQ, DEM et DOC sans écraser les URLs déjà existantes."""
        for rec in self:

            # Si aucun contexte valide → tout désactiver
            if not rec.ste_id or not rec.chq:
                rec.chq_pdf_url = False
                rec.dem_pdf_url = False
                rec.doc_pdf_url = False

                rec.chq_exist = 'chq_not_exists'
                rec.dem_exist = 'dem_not_exists'
                rec.doc_exist = 'doc_not_exists'
                continue

            # 🔹 Ne chercher sur Google Drive QUE si l'URL est absente
            if not rec.chq_pdf_url:
                rec.chq_pdf_url = rec._get_pdf_url("CHQ")

            if not rec.dem_pdf_url:
                rec.dem_pdf_url = rec._get_pdf_url("DEM")

            if not rec.doc_pdf_url:
                rec.doc_pdf_url = rec._get_pdf_url("DOC")

            # Mettre à jour les badges d’existence
            rec.chq_exist = 'chq_exists' if rec.chq_pdf_url else 'chq_not_exists'
            rec.dem_exist = 'dem_exists' if rec.dem_pdf_url else 'dem_not_exists'
            rec.doc_exist = 'doc_exists' if rec.doc_pdf_url else 'doc_not_exists'


    # ------------------------------------------------------------
    # DELETION REQUEST
    # ------------------------------------------------------------
    def action_request_deletion(self):
        self.ensure_one()
        return {
            'name': 'Demande de suppression',
            'type': 'ir.actions.act_window',
            'res_model': 'finance.deletion.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': self._name,
                'default_res_id': self.id,
            }
        }

    # 7) Override create/write
    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._onchange_find_talon()
        rec._sync_pdf_url()
        
        # --- Check Stock Alert ---
        try:
            talon = rec.talon_id
            # 1. Check if CURRENT talon is low
            if talon and talon.unused_chqs <= 20:
                # 2. Check for HEALTHY backups
                # A healthy backup is another talon for the SAME company that is 'actif' or 'coffre'
                # AND has a decent remaining stock (e.g., > 20).
                # The user's rule: "If another talon exists and can take over, no notification"
                # Reinforced rule: "If there is another talon... remaining chqs should be < 20 to trigger"
                # => This means we scan for ANY talon with > 20 unused cheques. If found -> No Alert.
                
                healthy_backups = self.env['finance.talon'].search_count([
                    ('ste_id', '=', rec.ste_id.id),
                    ('id', '!=', talon.id),
                    ('etat', 'in', ['actif', 'coffre']),
                    ('unused_chqs', '>', 20) 
                ])
                
                if healthy_backups == 0:
                    # Alert Condition Met: Current is low, and no healthy backup exists.
                    self.env['finance.cheque.request'].create_request(rec.ste_id)
        except Exception as e:
            # Prevent blocking cheque creation if alert system fails
            pass
            
        return rec

    def write(self, vals):
        res = super().write(vals)
        if "chq" in vals or "ste_id" in vals:
            self._onchange_find_talon()
            self._sync_pdf_url()
        return res

    # 8) Bouton ouverture PDF
    def action_open_pdf_chq(self):
        self.ensure_one()
        if self.chq_pdf_url:
            self.chq_exist = 'chq_exists'
            return {
                "type": "ir.actions.act_url",
                "url": self.chq_pdf_url,
                "target": "new",
            }
        self._sync_pdf_url()


        # 🔄 1) Si aucune URL → essayer de synchroniser maintenant
        if not self.chq_pdf_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "PDF CHQ introuvable",
                    "message": "Aucun PDF CHQ n'a été trouvé sur Google Drive pour ce chèque.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        # ✅ 3) PDF trouvé → ouvrir
        return {
            "type": "ir.actions.act_url",
            "url": self.chq_pdf_url,
            "target": "new",
        }
    # ------------------------------------------------------------
    # ACTION : ouvrir PDF DEM
    # ------------------------------------------------------------
    def action_open_pdf_dem(self):
        self.ensure_one()
        if self.dem_pdf_url:
            self.dem_exist = 'dem_exists'
            return {
                "type": "ir.actions.act_url",
                "url": self.dem_pdf_url,
                "target": "new",
            }
        self._sync_pdf_url()

        if not self.dem_pdf_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "PDF DEM introuvable",
                    "message": "Aucun PDF DEM n'a été trouvé dans Google Drive.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        return {
            "type": "ir.actions.act_url",
            "url": self.dem_pdf_url,
            "target": "new",
        }
    # ------------------------------------------------------------
    # ACTION : ouvrir PDF DOC
    # ------------------------------------------------------------
    def action_open_pdf_doc(self):
        self.ensure_one()
        if self.doc_pdf_url:
            self.doc_exist = 'doc_exists'
            return {
                "type": "ir.actions.act_url",
                "url": self.doc_pdf_url,
                "target": "new",
            }
        self._sync_pdf_url()

        if not self.doc_pdf_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "PDF DOC introuvable",
                    "message": "Aucun PDF DOC n'a été trouvé dans Google Drive.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        return {
            "type": "ir.actions.act_url",
            "url": self.doc_pdf_url,
            "target": "new",
        }

    # ------------------------------------------------------------
    # CRON : synchroniser les PDF CHQ tous les jours
    # ------------------------------------------------------------
    @api.model
    def cron_sync_all_chq_pdf(self):
        """Met à jour les liens PDF manquants pour les chèques incomplets."""
        records = self.search([
            ('chq', '!=', False),
            ('ste_id', '!=', False),
            ('dem_pdf_url', '=', False),
        ])
        records._sync_pdf_url()

    # ------------------------------------------------------------
    # CRON : check existence one time
    # ------------------------------------------------------------
    @api.model
    def cron_sync_all_pdf(self):
        """
        Cron qui imite le comportement du bouton pour TOUS les chèques.
        - Met à jour les flags si les URLs existent déjà.
        - Sinon lance _sync_pdf_url() pour récupérer CHQ, DEM, DOC.
        """
        records = self.search([])

        for rec in records:

            # --- 1) Si les URLs existent déjà, mise à jour des états ---
            rec.chq_exist = 'chq_exists' if rec.chq_pdf_url else 'chq_not_exists'
            rec.dem_exist = 'dem_exists' if rec.dem_pdf_url else 'dem_not_exists'
            rec.doc_exist = 'doc_exists' if rec.doc_pdf_url else 'doc_not_exists'

            # --- 2) Si au moins une URL manque -> aller chercher dans Drive ---
            if not rec.chq_pdf_url or not rec.dem_pdf_url or not rec.doc_pdf_url:
                rec._sync_pdf_url()
            rec._compute_existance_tag()
            rec._compute_existance_dem_tag()
            rec._compute_existance_doc_tag()

        return True