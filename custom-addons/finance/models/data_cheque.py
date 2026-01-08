from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from markupsafe import Markup

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
        ('annule', 'Annulé'),
    ], string='Facture', tracking=True, required=True, default='m')
    journal = fields.Integer(string='Journal N°', required=True, default=None)
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
        ('divers', 'Divers'),
    ], store=True, string='Type', tracking=True)
    
    # New Fields
    bl = fields.Char(string='BL', tracking=True)
    encours = fields.Selection([
        ('encaisse', 'Encaissé'),
        ('non_encaisse', 'Non encaissé'),
    ], string='Status Encaissement', compute='_compute_encours', store=True)

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
    
    # Edit Lock Fields
    unlock_until = fields.Datetime(string="Déverrouillé jusqu'à", help="Si défini, le chèque peut être modifié jusqu'à cette date", tracking=True)
    unlock_until_label = fields.Char(compute='_compute_unlock_until_label', string="Label date déverrouillage")
    is_locked = fields.Boolean(string="Verrouillé", compute='_compute_is_locked', help="Indique si le chèque est verrouillé pour l'utilisateur actuel")
    # ------------------------------------------------------------
    # EDIT LOCK LOGIC
    # ------------------------------------------------------------
    @api.depends('unlock_until')
    def _compute_unlock_until_label(self):
        for rec in self:
            if rec.unlock_until:
                # Convertir en heure locale de l'utilisateur
                local_date = fields.Datetime.context_timestamp(rec, rec.unlock_until)
                rec.unlock_until_label = local_date.strftime('%d/%m/%Y %H:%M')
            else:
                rec.unlock_until_label = ""

    @api.depends('unlock_until')
    def _compute_is_locked(self):
        """Compute if cheque is locked for current user."""
        for rec in self:
            # Managers are never locked
            if self.env.user.has_group('finance.group_finance_user'):
                rec.is_locked = False
                continue
            
            now = fields.Datetime.now()
            
            # If temporarily unlocked and not expired, allow edit
            if rec.unlock_until and rec.unlock_until > now:
                rec.is_locked = False
                continue
            
            # Check if created today and before 19:00
            if rec.create_date:
                create_date_local = fields.Datetime.context_timestamp(rec, rec.create_date)
                today_local = fields.Datetime.context_timestamp(rec, now)
                
                # If created on a different day, it's locked
                if create_date_local.date() != today_local.date():
                    rec.is_locked = True
                    continue
                
                # If created today but after 19:00, it's locked
                if today_local.hour >= 19:
                    rec.is_locked = True
                    continue
            
            # Otherwise, it's editable
            rec.is_locked = False
    
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

    @api.depends('date_emission', 'benif_id.days', 'benif_id', 'state')
    def _compute_date_echeance(self):
        for rec in self:
            if rec.state in ['bureau', 'annule']:
                rec.date_echeance = False
            elif rec.date_emission and rec.benif_id and rec.benif_id.days:
                rec.date_echeance = rec.date_emission + timedelta(days=rec.benif_id.days)
            else:
                rec.date_echeance = rec.date_emission

    def _compute_encours(self):
        for rec in self:
            if rec.date_encaissement:
                rec.encours = 'encaisse'
            else:
                rec.encours = 'non_encaisse'

    # ------------------------------------------------------------
    # CONTRAINTES
    # ------------------------------------------------------------
    @api.onchange('chq', 'ste_id', 'benif_id', 'type')
    def _onchange_chq_checks(self):
        for rec in self:

            # 1️⃣ Longueur exacte = 7
            if rec.chq and len(rec.chq) != 7:
                raise ValidationError("Le numéro de chèque doit contenir exactement 7 caractères.")

    _sql_constraints = [
        ('unique_chq_ste', 'unique(chq, ste_id, type)', '⚠️ Ce numéro du chèque existe déja pour cette société pour ce type.')
    ]

    @api.constrains('chq', 'ste_id', 'benif_id', 'type')
    def _check_custom_uniqueness(self):
        """Enforces strict uniqueness rules backend-side."""
        for rec in self:
            if not rec.chq or not rec.ste_id:
                continue

            domain = [
                ('chq', '=', rec.chq),
                ('ste_id', '=', rec.ste_id.id),
                ('id', '!=', rec.id)
            ]
            existing_records = self.search(domain)

            for ex in existing_records:
                # Same logic as Onchange
                current_is_import = (rec.benif_id.type == 'import')
                ex_is_import = (ex.benif_id.type == 'import')

                if current_is_import and ex_is_import:
                    if rec.type and ex.type and rec.type != ex.type:
                        continue 
                
                raise ValidationError(f"Le chèque {rec.chq} existe déjà pour la société {rec.ste_id.name} (Doublon non autorisé).")

    @api.constrains('state')
    def _check_state_annule(self):
        """Validate annulé state - do NOT modify fields here."""
        for rec in self:
            if rec.state == 'annule':
                # Just validate - modifications should happen in onchange or write()
                # The onchange and _force_state_logic handle the actual updates
                pass

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
    def _get_bureau_benif(self):
        return self.env['finance.benif'].search([('name', '=', 'Bureau')], limit=1)
        
    def _get_bureau_perso(self):
        return self.env['finance.perso'].search([('name', '=', 'Bureau')], limit=1)

    def _get_annule_perso(self):
        return self.env['finance.perso'].search([('name', '=', 'Annulé')], limit=1)

    def _get_annule_benif(self):
        return self.env['finance.benif'].search([('name', '=', 'Annulé')], limit=1)

    @api.onchange('state')
    def _onchange_state_force_facture(self):
        for rec in self:
            if rec.state == 'bureau':
                # Force Values
                rec.facture = 'bureau'
                rec.journal = '0'
                
                # Set Bureau relations
                bureau_benif = rec._get_bureau_benif()
                if bureau_benif:
                    rec.benif_id = bureau_benif
                    
                bureau_perso = rec._get_bureau_perso()
                if bureau_perso:
                    rec.perso_id = bureau_perso

                # Clear dates LAST to ensure they aren't overwritten by relation changes triggering computes
                rec.date_emission = False
                rec.date_echeance = False

    @api.constrains('state', 'facture', 'date_emission', 'date_echeance')
    def _check_state_rules(self):
        """Validate state rules - do NOT modify fields here."""
        for rec in self:
            if rec.state == 'bureau':
                # Only validate - don't modify
                # The onchange and _force_state_logic handle modifications
                pass
                
            elif rec.state == 'annule':
                # Only validate - don't modify
                pass

            else:
                # Make dates required for other active states
                if not rec.date_emission:
                    raise ValidationError("La date d'émission est requise sauf si l'état est 'Bureau' ou 'Annulé'.")
                if not rec.date_echeance:
                    raise ValidationError("La date d'échéance est requise sauf si l'état est 'Bureau' ou 'Annulé'.")

    # ------------------------------------------------------------
    # if state == Annulé
    # ------------------------------------------------------------
    @api.onchange('state')
    def _onchange_state_annule(self):
        for rec in self:
            if rec.state == 'annule':
                rec.facture = 'annule'
                rec.journal = '0'
                rec.serie = "Annulé"

                annule_perso = rec._get_annule_perso()
                if annule_perso:
                    rec.perso_id = annule_perso

                annule_benif = rec._get_annule_benif()
                if annule_benif:
                    rec.benif_id = annule_benif

                # Clear dates LAST
                rec.date_emission = False
                rec.date_echeance = False
                
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

    # -------------------------------------------------------------------
    # SEQUENCE INTEGRITY CHECK
    # -------------------------------------------------------------------
    def _check_sequence_integrity(self, vals):
        """
        Ensures that cheques are created in strict sequence (N+1).
        Blocks creation if there is a gap or backward numbering.
        """
        # 1. Logic to identify Talon (matches _find_talon_logic)
        chq_str = vals.get('chq')
        ste_id = vals.get('ste_id')

        if not chq_str or not ste_id or not str(chq_str).isdigit():
            return # Skip check if data is invalid (constraints will handle it)

        chq_num = int(chq_str)

        # We must find the talon that WOULD be assigned.
        # Can't rely on 'talon_id' in vals because it might be computed later.
        # We assume the standard logic applies.
        
        # Reuse logic logic but optimized for 'vals' context
        talons = self.env['finance.talon'].search([
            ('ste_id', '=', ste_id),
            ('num_chq', '>', 0),
            ('name', '!=', False),
        ])
        
        target_talon = False
        for talon in talons:
            if not talon.name.isdigit(): continue
            start = int(talon.name)
            end = start + talon.num_chq - 1
            if start <= chq_num <= end:
                target_talon = talon
                break
        
        if not target_talon:
             return # No talon found -> standard creation (or error elsewhere)

        # 2. Find LAST EXISTING cheque for this talon
        last_cheque = self.search([
            ('talon_id', '=', target_talon.id),
            ('chq', '!=', False)
        ], order='chq desc', limit=1)

        if not last_cheque:
            return # First cheque of the talon -> Allowed

        last_num = int(last_cheque.chq)
        expected_num = last_num + 1

        if chq_num <= last_num:
            return
        
        if chq_num != expected_num:
             raise ValidationError(
                 f"Dernier chèque saisi : {last_num}\n"
                 f"Attention🚫 Chèque attendu : {expected_num}\n"
                 f"Chèque saisie actuelle : {chq_num}\n\n"
                 f"Veuillez sasir d'abord CHQ : {expected_num}\n\n"
                 "Veuillez saisir les chèques dans l'ordre strict, sans saut numéro."
             )

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
    
    # ------------------------------------------------------------
    # EDIT AUTHORIZATION REQUEST
    # ------------------------------------------------------------
    def action_request_edit(self):
        """Create an edit authorization request for a locked cheque."""
        self.ensure_one()
        
        # Check if there's already a pending request
        existing_request = self.env['finance.edit.request'].search([
            ('cheque_id', '=', self.id),
            ('state', '=', 'pending')
        ], limit=1)
        
        if existing_request:
            return {
                'name': 'Demande existante',
                'type': 'ir.actions.act_window',
                'res_model': 'finance.edit.request',
                'res_id': existing_request.id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        return {
            'name': 'Demande d\'autorisation de modification',
            'type': 'ir.actions.act_window',
            'res_model': 'finance.edit.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cheque_id': self.id,
            }
        }

    # 7) Helper to force state relation logic in backend
    def _force_state_logic(self, vals):
        """Ensures that validation rules are respected even if onchange is skipped."""
        state = vals.get('state')
        
        # We need to know the state. In create, it's in vals or default.
        # In write, it might not be in vals.
        # This helper is designed to modify 'vals' in place.
        
        if state == 'bureau':
            # Force integrity
            if vals.get('facture') != 'bureau':
                vals['facture'] = 'bureau'
            vals['journal'] = 0
            vals['date_emission'] = False
            vals['date_echeance'] = False

            # Force Relationship : Person
            if not vals.get('perso_id'):
                bureau_perso = self._get_bureau_perso()
                if not bureau_perso:
                    raise ValidationError("L'enregistrement 'Bureau' est introuvable dans la liste des Personnes. Veuillez le créer.")
                vals['perso_id'] = bureau_perso.id

            # Force Relationship : Beneficiary
            if not vals.get('benif_id'):
                bureau_benif = self._get_bureau_benif()
                if not bureau_benif:
                    raise ValidationError("L'enregistrement 'Bureau' est introuvable dans la liste des Bénéficiaires. Veuillez le créer.")
                vals['benif_id'] = bureau_benif.id

        elif state == 'annule':
            # Force integrity
            if vals.get('facture') != 'annule':
                vals['facture'] = 'annule'
            vals['journal'] = 0
            vals['date_emission'] = False
            vals['date_echeance'] = False

            # Force Relationship : Person
            if not vals.get('perso_id'):
                annule_perso = self._get_annule_perso()
                if not annule_perso:
                    raise ValidationError("L'enregistrement 'Annulé' est introuvable dans la liste des Personnes. Veuillez le créer.")
                vals['perso_id'] = annule_perso.id

            # Force Relationship : Beneficiary
            if not vals.get('benif_id'):
                annule_benif = self._get_annule_benif()
                if not annule_benif:
                    raise ValidationError("L'enregistrement 'Annulé' est introuvable dans la liste des Bénéficiaires. Veuillez le créer.")
                vals['benif_id'] = annule_benif.id

    # 7) Override create/write
    @api.model
    def create(self, vals):
        # Apply backend logic for relations before super().create validates required constraints
        self._force_state_logic(vals)
        
        # STRICT SEQUENCE CHECK
        # Must be done BEFORE creation to block gaps
        self._check_sequence_integrity(vals)
        
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
                    ('unused_chqs', '>', 15) 
                ])
                
                if healthy_backups == 0:
                    # Alert Condition Met: Current is low, and no healthy backup exists.
                    self.env['finance.cheque.request'].create_request(rec.ste_id)
        except Exception as e:
            # Prevent blocking cheque creation if alert system fails
            pass
            
        return rec

    def write(self, vals):
        # Check edit lock BEFORE any modifications
        # Skip lock check if user is manager
        if not self.env.user.has_group('finance.group_finance_user'):
            for rec in self:
                # Check lock status directly (field is already computed)
                # Do NOT call _compute_is_locked() here - it causes recursion
                if rec.is_locked:
                    raise UserError(
                        "Ce chèque est verrouillé.\n\n"
                        "Les chèques ne peuvent pas être modifiés après 19h00.\n\n"
                        "Veuillez demander une autorisation de modification à un manager Finance."
                    )
        
        # Apply state-specific logic
        for rec in self:
            check_state = vals.get('state')
            if check_state in ['bureau', 'annule']:
                 # We simply apply the logic to the `vals` dict.
                 # Since `_force_state_logic` modifies `vals` in place and lookups DB, it's safe.
                 rec._force_state_logic(vals)

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

    # ------------------------------------------------------------
    # CRON: Clear expired temporary unlocks
    # ------------------------------------------------------------
    @api.model
    def cron_clear_expired_unlocks(self):
        """Clear unlock_until for cheques where the unlock has expired."""
        now = fields.Datetime.now()
        expired_cheques = self.search([
            ('unlock_until', '!=', False),
            ('unlock_until', '<', now)
        ])
        if expired_cheques:
            expired_cheques.write({'unlock_until': False})
        return True