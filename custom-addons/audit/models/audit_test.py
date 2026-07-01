from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests
import json
import base64
import io
import csv
from markupsafe import Markup

class AuditTest(models.Model):
    _name = 'audit.test'
    _description = 'Test Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Titre', required=True, tracking=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    
    # Booleans for tests
    exactitude = fields.Boolean(string='Exactitude', tracking=True)
    cutoff = fields.Boolean(string='Cut-off', tracking=True)
    classification = fields.Boolean(string='Classification', tracking=True)
    
    # Files
    facture_pdf = fields.Binary(string='Facture PDF', attachment=True)
    facture_filename = fields.Char(string='Nom Facture')
    
    compta_excel = fields.Binary(string='Sélections de comptabilité (Excel)', attachment=True)
    compta_excel_filename = fields.Char(string='Nom Compta Excel')

    def action_verify_exactitude(self):
        self.ensure_one()
        if not self.facture_pdf or not self.compta_excel:
            raise ValidationError("Veuillez d'abord uploader la facture (PDF) ET les sélections de comptabilité (Excel).")

        api_key = self.env['ir.config_parameter'].sudo().get_param('tresorerie_chq.gemini_key')
        if not api_key:
            raise ValidationError("La clé API Google Gemini n'est pas configurée (tresorerie_chq.gemini_key).")

        # Lecture du fichier Excel
        try:
            import openpyxl
            excel_bytes = base64.b64decode(self.compta_excel)
            wb = openpyxl.load_workbook(filename=io.BytesIO(excel_bytes), data_only=True)
            
            # Recherche de la feuille "sélection"
            sheet_name = None
            for sn in wb.sheetnames:
                if 'sélection' in sn.lower() or 'selection' in sn.lower():
                    sheet_name = sn
                    break
            
            if not sheet_name:
                sheet = wb.active
            else:
                sheet = wb[sheet_name]
            
            csv_data = io.StringIO()
            writer = csv.writer(csv_data)
            for row in sheet.iter_rows(values_only=True):
                writer.writerow([str(c) if c is not None else '' for c in row])
            
            compta_text = csv_data.getvalue()
        except Exception as e:
            raise ValidationError(f"Erreur lors de la lecture du fichier Excel : {str(e)}")

        prompt_text = f"""Vous êtes un auditeur comptable. Vous avez reçu :
1. Une facture en pièce jointe (PDF)
2. Les données de la feuille 'sélection' de la comptabilité au format CSV ci-dessous :

DONNÉES COMPTABLES (CSV) :
{compta_text[:20000]}

Votre tâche :
1. Lire le numéro de la facture et son montant total TTC (ou à payer) dans le PDF de la facture.
2. Chercher ce numéro de facture dans les données comptables CSV fournies ci-dessus. Sachez que le numéro de la facture se trouve spécifiquement dans la colonne 'Numéro Fact' (qui correspond à la colonne H dans le fichier d'origine).
3. Extraire le montant qui est associé à cette facture dans le CSV.
4. Vérifier si les deux montants sont égaux (attention aux formats de nombres, ex: 1000.50 et 1 000,50).

Retournez UNIQUEMENT un objet JSON valide, sans markdown.
Exemple attendu :
{{
    "invoice_number": "le numéro trouvé sur la facture PDF",
    "invoice_amount": le_montant_trouvé_sur_la_facture_en_nombre,
    "compta_amount": le_montant_trouvé_dans_la_compta_en_nombre_ou_null,
    "is_exact": true_ou_false
}}"""

        # 1. Upload the PDF to Gemini File API
        pdf_bytes = base64.b64decode(self.facture_pdf)
        upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={api_key}"
        upload_headers = {
            "X-Goog-Upload-Protocol": "raw",
            "X-Goog-Upload-Header-Content-Type": "application/pdf",
            "Content-Type": "application/pdf"
        }
        try:
            upload_resp = requests.post(upload_url, headers=upload_headers, data=pdf_bytes, timeout=120)
            if upload_resp.status_code != 200:
                err_msg = upload_resp.json().get("error", {}).get("message", upload_resp.text)
                raise ValidationError(f"Erreur lors de l'upload du PDF vers Gemini : {err_msg}")
            
            file_info = upload_resp.json().get("file", {})
            file_uri = file_info.get("uri")
            if not file_uri:
                raise ValidationError("Impossible de récupérer l'URI du fichier après l'upload.")
        except Exception as e:
            raise ValidationError(f"Erreur de communication lors de l'upload vers l'IA : {str(e)}")

        # 2. Generate Content using Gemini
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt_text
                        },
                        {
                            "fileData": {
                                "mimeType": "application/pdf",
                                "fileUri": file_uri
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            if resp.status_code != 200:
                err_msg = resp.json().get("error", {}).get("message", resp.text)
                raise ValidationError(f"Erreur de l'API Gemini : {err_msg}")
            
            ai_data = resp.json()
        except Exception as e:
            raise ValidationError(f"Erreur de communication avec l'IA : {str(e)}")

        try:
            raw_content = ai_data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise ValidationError("L'IA n'a retourné aucune donnée lisible.")

        try:
            result = json.loads(raw_content)
        except Exception:
            raise ValidationError(f"L'IA a retourné un format JSON invalide : {raw_content}")

        if result.get("is_exact") is True:
            self.exactitude = True
            msg = f"<div style='color: green;'><i class='fa fa-check-circle'></i> <b>Test d'exactitude réussi (via Gemini)</b><br/>Facture: {result.get('invoice_number')} | Montant: {result.get('invoice_amount')} = {result.get('compta_amount')}</div>"
        else:
            self.exactitude = False
            msg = f"<div style='color: red;'><i class='fa fa-times-circle'></i> <b>Test d'exactitude échoué ou facture non trouvée</b><br/>Facture: {result.get('invoice_number')} | Montant Facture: {result.get('invoice_amount')} | Montant Compta: {result.get('compta_amount')}</div>"

        self.message_post(body=Markup(msg))
