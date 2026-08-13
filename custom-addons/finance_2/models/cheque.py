from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta

class Finance2Cheque(models.Model):
    _name = 'finance2.cheque'
    _description = 'Chèque Physique (Finance 2)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _sql_constraints = [
        ('unique_cheque_ste', 'unique(name, ste_id)', 'Erreur : Ce numéro de chèque existe déjà pour cette société !')
    ]

    name = fields.Char(string='N° Chèque', required=False, tracking=True)
    ste_id = fields.Many2one('finance2.ste', string='Société', required=False, tracking=True)
    benif_id = fields.Many2one('finance2.benif', string='Bénéficiaire', tracking=True)
    
    amount_total = fields.Float(string='Montant Total', tracking=True)

    total_surestarie = fields.Float(string='Total Surestarie', compute='_compute_totals')
    total_magasinage = fields.Float(string='Total Magasinage', compute='_compute_totals')
    total_change = fields.Float(string='Total Change', compute='_compute_totals')
    total_inspection = fields.Float(string='Total Inspection', compute='_compute_totals')
    total_repartitions = fields.Float(string='Total Répartitions', compute='_compute_totals')

    @api.depends('repartition_ids.amount', 'repartition_ids.type')
    def _compute_totals(self):
        for rec in self:
            rec.total_surestarie = sum(r.amount for r in rec.repartition_ids if r.type == 'surestarie')
            rec.total_magasinage = sum(r.amount for r in rec.repartition_ids if r.type == 'magasinage')
            rec.total_change = sum(r.amount for r in rec.repartition_ids if r.type == 'change')
            rec.total_inspection = sum(r.amount for r in rec.repartition_ids if r.type == 'inspection')
            rec.total_repartitions = sum(r.amount for r in rec.repartition_ids)
    
    type = fields.Selection([('cheque', 'Chèque'), ('effet', 'Effet')], string='Type', default='cheque', tracking=True)
    chq_certifie = fields.Boolean(string='Chq certifié', tracking=True)
    journal = fields.Char(string='Journal', tracking=True)
    personne_id = fields.Many2one('finance2.personne', string='Personnes', tracking=True)
    serie_facture = fields.Char(string='Série de facture', tracking=True)
    
    date_emission = fields.Date(string="Date d'émission", tracking=True)
    date_echeance = fields.Date(string="Date d'échéance", tracking=True)
    date_encaissement = fields.Date(string="Date d'encaissement", tracking=True)
    
    commentaire = fields.Text(string="Commentaire")
    
    # Documents
    chq_vide_pdf = fields.Binary(string='Chèque vide (PDF)', attachment=True)
    chq_vide_filename = fields.Char(string='Nom du fichier Chèque vide')
    
    doc_pdf = fields.Binary(string='Documentation (PDF)', attachment=True)
    doc_filename = fields.Char(string='Nom du fichier Documentation')
    
    # Workflow Status
    is_admin = fields.Boolean(compute='_compute_is_admin')

    def _compute_is_admin(self):
        for rec in self:
            rec.is_admin = self.env.user.has_group('finance_2.group_finance2_admin')

    admin_state = fields.Selection(related='state', readonly=False, tracking=False)
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('reserve', 'Réserve'),
        ('actif', 'Actif'),
        ('cloture', 'Clôturé'),
        ('annule', 'Annulé'),
    ], string='État', default='brouillon', tracking=True, required=True)
    
    # Suivi Logistique
    remis_a_id = fields.Many2one('finance2.personne', string='Remis à', tracking=True)
    date_remise = fields.Date(string='Date de remise (Actif)', tracking=True)
    
    # Répartitions
    repartition_ids = fields.One2many('finance2.repartition', 'cheque_id', string='Répartitions')


    @api.model_create_multi
    def create(self, vals_list):
        records = super(Finance2Cheque, self).create(vals_list)
        for rec in records:
            if rec.chq_vide_pdf and not rec.name:
                rec._extract_empty_cheque_data()
        return records

    def write(self, vals):
        res = super(Finance2Cheque, self).write(vals)
        if 'chq_vide_pdf' in vals and vals['chq_vide_pdf']:
            for rec in self:
                if not rec.name:
                    rec._extract_empty_cheque_data()
        return res

    def _extract_empty_cheque_data(self):
        for rec in self:
            if not rec.chq_vide_pdf:
                continue

            api_key = self.env['ir.config_parameter'].sudo().get_param('finance.gemini_api_key')
            if not api_key:
                rec.message_post(body="<div style='color:red;'>Erreur: finance.gemini_api_key est vide ou non configuré.</div>")
                continue

            import requests
            import json
            import re

            pdf_bytes = rec.chq_vide_pdf.decode('utf-8') if isinstance(rec.chq_vide_pdf, bytes) else rec.chq_vide_pdf
            import base64
            try:
                pdf_bytes_decoded = base64.b64decode(pdf_bytes)
            except Exception:
                pdf_bytes_decoded = pdf_bytes # Just in case it's not base64 encoded properly

            stes = self.env['finance2.ste'].sudo().search([])
            stes_names = ", ".join([f"{s.name} ({s.raison_social or ''})" for s in stes])
            
            persos = self.env['finance2.personne'].sudo().search([])
            persos_names = ", ".join(persos.mapped('name'))
            
            benifs = self.env['finance2.benif'].sudo().search([])
            benifs_names = ", ".join(benifs.mapped('name'))

            prompt_text = f"""Vous êtes un assistant financier. Vous recevez un scan d'un chèque vide.
Votre but est d'extraire les informations suivantes.
1. "chq": Le numéro du chèque (généralement 7 chiffres, ex: 2102888).
2. "ste": La société émettrice. Cherchez la raison sociale inscrite sur le chèque, et comparez avec la liste suivante : {stes_names}. Extrayez l'abréviation correspondante (la valeur avant les parenthèses).
3. "date_emission": La date qui se situe sur le cachet en dessous (la première date inscrite), au format YYYY-MM-DD.
4. "personne": La personne écrite sur le cachet (sur la deuxième ligne). Essayez de faire correspondre avec l'un de ces noms : {persos_names}.
5. "journal": Le numéro écrit manuellement en haut. Il peut être sous forme "Wxx-Journal" (ex: "W33-12", extrayez uniquement "12") ou bien simplement un chiffre écrit seul (ex: "12"). Extrayez uniquement le numéro du journal.
6. "beneficiaire": Le bénéficiaire (à l'ordre de). Essayez de faire correspondre avec l'un de ces noms : {benifs_names}.

Retournez UNIQUEMENT un objet JSON valide, sans markdown.
Exemple:
{{
  "chq": "2102888",
  "ste": "SN",
  "date_emission": "2026-05-18",
  "personne": "Abderzak",
  "journal": "12",
  "beneficiaire": "AFRICONTAINER"
}}"""

            # 1. Upload the file to Gemini
            upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={api_key}"
            upload_headers = {
                "X-Goog-Upload-Protocol": "raw",
                "X-Goog-Upload-Header-Content-Type": "application/pdf",
                "Content-Type": "application/pdf"
            }
            try:
                upload_resp = requests.post(upload_url, headers=upload_headers, data=pdf_bytes_decoded, timeout=120)
                if upload_resp.status_code != 200:
                    rec.message_post(body=f"<div style='color:red;'>Erreur Gemini Upload: {upload_resp.text[:500]}</div>")
                    continue
                
                file_uri = upload_resp.json().get("file", {}).get("uri")
                if not file_uri:
                    rec.message_post(body="<div style='color:red;'>Impossible de récupérer l'URI Gemini.</div>")
                    continue
            except Exception as e:
                rec.message_post(body=f"<div style='color:red;'>Exception Gemini Upload: {str(e)}</div>")
                continue

            # 2. Call generateContent
            gemini_model = self.env['ir.config_parameter'].sudo().get_param('finance.gemini_model', 'gemini-pro-latest')
            gemini_model = gemini_model.replace('models/', '')
            # Forcer gemini-pro-latest si la valeur est l'ancienne qui crashait
            if gemini_model in ['gemini-1.5-flash-latest', 'gemini-flash-latest', 'gemini-1.5-flash']:
                gemini_model = 'gemini-pro-latest'

            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}"

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt_text},
                            {"fileData": {"mimeType": "application/pdf", "fileUri": file_uri}}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.0,
                    "responseMimeType": "application/json"
                }
            }

            headers = {
                "Content-Type": "application/json"
            }

            try:
                resp = requests.post(gemini_url, headers=headers, json=payload, timeout=120)
                if resp.status_code != 200:
                    rec.message_post(body=f"<div style='color:red;'>Erreur API Gemini ({resp.status_code}): {resp.text[:500]}</div>")
                    continue
                ai_data = resp.json()
            except Exception as e:
                rec.message_post(body=f"<div style='color:red;'>Exception API Gemini: {str(e)}</div>")
                continue

            raw_content = ""
            candidates = ai_data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    raw_content = parts[0].get("text", "")

            if not raw_content:
                rec.message_post(body="<div style='color:red;'>Erreur: Contenu vide retourné par Gemini.</div>")
                continue
                
            clean_content = re.sub(r'^```(json)?', '', raw_content.strip(), flags=re.IGNORECASE)
            clean_content = re.sub(r'```$', '', clean_content.strip()).strip()

            try:
                result = json.loads(clean_content)
            except Exception as e:
                rec.message_post(body=f"<div style='color:red;'>Erreur de lecture JSON: {str(e)} - Contenu: {clean_content[:200]}</div>")
                continue


            ste_code = result.get('ste', '')
            ste_record = False
            if ste_code:
                ste_record = self.env['finance2.ste'].search([('name', '=ilike', ste_code)], limit=1)
                
            perso_name = result.get('personne', '')
            perso_record = False
            if perso_name:
                perso_record = self.env['finance2.personne'].search([('name', '=ilike', perso_name)], limit=1)
                if not perso_record:
                    perso_record = self.env['finance2.personne'].search([('name', 'ilike', perso_name)], limit=1)
                    
            benif_name = result.get('beneficiaire', '')
            benif_record = False
            if benif_name:
                benif_record = self.env['finance2.benif'].search([('name', '=ilike', benif_name)], limit=1)
                if not benif_record:
                    benif_record = self.env['finance2.benif'].search([('name', 'ilike', benif_name)], limit=1)
            
            update_vals = {}
            final_chq = result.get('chq')
            final_ste_id = ste_record.id if ste_record else False

            if final_chq:
                update_vals['name'] = final_chq
            if final_ste_id:
                update_vals['ste_id'] = final_ste_id
            if perso_record:
                update_vals['personne_id'] = perso_record.id
            if benif_record:
                update_vals['benif_id'] = benif_record.id
            if result.get('date_emission'):
                update_vals['date_emission'] = result.get('date_emission')
            
            raw_journal = str(result.get('journal', ''))
            match = re.search(r'\d+', raw_journal)
            if match:
                update_vals['journal'] = match.group()
            
            if update_vals:
                rec.sudo().write(update_vals)

            if not final_ste_id or not final_chq:
                from markupsafe import Markup
                rec.message_post(body=Markup(
                    "<div style='border-left:4px solid #ffc107;padding:8px 12px;background:#fff8e1;border-radius:4px;'>"
                    "<span style='color:#ffc107;font-size:15px;'><i class='fa fa-exclamation-triangle'></i>&nbsp;<b>IA : Extraction incomplète</b></span>"
                    f"<p style='margin:4px 0 0;'>L'IA n'a pas pu identifier le numéro de chèque ou la société ({ste_code}). Veuillez remplir ces champs manuellement.</p>"
                    "</div>"
                ))
            else:
                from markupsafe import Markup
                rec.message_post(body=Markup(
                    "<div style='border-left:4px solid #007bff;padding:8px 12px;background:#f8f9fa;border-radius:4px;'>"
                    "<span style='color:#007bff;font-size:15px;'><i class='fa fa-robot'></i>&nbsp;<b>IA : Chèque identifié</b></span>"
                    f"<p style='margin:4px 0 0;'>Le système a extrait le numéro <b>{final_chq}</b>, la société <b>{ste_code}</b>, la date d'émission <b>{result.get('date_emission', '')}</b>, la personne <b>{perso_name}</b>, le journal <b>{update_vals.get('journal', '')}</b> et le bénéficiaire <b>{benif_name}</b>.</p>"
                    "</div>"
                ))

    def action_confirmer(self):
        for rec in self:
            missing_fields = []
            if not rec.journal:
                missing_fields.append("Journal")
            if not rec.name:
                missing_fields.append("N° Chèque")
            if not rec.date_emission:
                missing_fields.append("Date d'émission")
            if not rec.ste_id:
                missing_fields.append("Société")
                
            if missing_fields:
                raise UserError("Vous ne pouvez pas confirmer ce chèque car les informations suivantes sont manquantes : " + ", ".join(missing_fields))
                
            rec.state = 'reserve'
            
    def action_remettre_finance(self):
        for rec in self:
            rec.state = 'brouillon'
            rec.remis_a_id = False
            rec.date_remise = False
            
    def action_mettre_actif(self):
        for rec in self:
            if not rec.remis_a_id:
                raise UserError("Vous devez renseigner le champ 'Remis à' avant de passer le chèque à l'état Actif.")
            rec.state = 'actif'
            rec.date_remise = fields.Date.today()
            
    def action_cloturer(self):
        for rec in self:
            missing_fields = []
            if not rec.amount_total:
                missing_fields.append("Montant Total")
            if not rec.date_echeance:
                missing_fields.append("Date d'échéance")
                
            if missing_fields:
                raise UserError("Vous ne pouvez pas clôturer ce chèque car les informations suivantes sont manquantes : " + ", ".join(missing_fields))
                
            rec.state = 'cloture'
            
    def action_annuler(self):
        for rec in self:
            rec.state = 'annule'

    @api.model
    def _cron_check_actif_5_days(self):
        """Cron job that checks for cheques in 'actif' state for more than 5 days and sends a reminder."""
        limit_date = fields.Date.today() - timedelta(days=5)
        cheques = self.search([
            ('state', '=', 'actif'),
            ('date_remise', '<=', limit_date)
        ])
        for cheque in cheques:
            # Send message to chatter
            cheque.message_post(
                body=f"Rappel : Ce chèque est à l'état Actif depuis plus de 5 jours (remis le {cheque.date_remise}).",
                subtype_xmlid='mail.mt_note'
            )



    def force_brouillon(self):
        for rec in self:
            rec.state = 'brouillon'

    def force_reserve(self):
        for rec in self:
            rec.state = 'reserve'

    def force_actif(self):
        for rec in self:
            rec.state = 'actif'

    def force_cloture(self):
        for rec in self:
            rec.state = 'cloture'

class Finance2Repartition(models.Model):
    _name = 'finance2.repartition'
    _description = 'Répartition de Chèque'

    cheque_id = fields.Many2one('finance2.cheque', string='Chèque', required=True, ondelete='cascade')
    amount = fields.Float(string='Montant', required=True)
    serie_facture = fields.Char(string='Série de facture')
    bl = fields.Char(string='BL')
    journal = fields.Char(string='Journal')
    type = fields.Selection([
        ('surestarie', 'Surestarie'),
        ('magasinage', 'Magasinage'),
        ('change', 'Change'),
        ('inspection', 'Inspection')
    ], string='Type')
