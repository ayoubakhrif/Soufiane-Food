from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests
import json
import base64
from markupsafe import Markup
from datetime import datetime

class AuditInvoice(models.Model):
    _name = 'audit.invoice'
    _description = 'Facture Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Référence', default="Nouveau")
    
    # Required Fields
    supplier = fields.Char(string='Fournisseur', tracking=True)
    invoice_number = fields.Char(string='N° facture', tracking=True)
    invoice_date = fields.Date(string='Date facture', tracking=True)
    
    # Document PDF
    invoice_pdf = fields.Binary(string='Facture PDF', attachment=True, required=True)
    invoice_filename = fields.Char(string='Nom du fichier')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('extracted', 'Extrait'),
    ], string='État', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            # Basic sequencing without ir.sequence to keep it independent
            last_rec = self.search([], limit=1, order='id desc')
            new_id = (last_rec.id + 1) if last_rec else 1
            vals['name'] = f"AUDIT/{datetime.now().year}/{new_id:04d}"
        return super(AuditInvoice, self).create(vals)

    def action_extract_ai(self):
        """Appel à OpenAI pour extraire les données de la facture PDF."""
        self.ensure_one()
        if not self.invoice_pdf:
            raise ValidationError("Veuillez d'abord uploader une facture PDF.")

        # Récupération de la clé API depuis les paramètres système
        api_key = self.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not api_key:
            raise ValidationError("La clé API OpenAI n'est pas configurée (whatsapp_stock.openai_key).")

        # Préparation du fichier
        pdf_b64 = self.invoice_pdf.decode('utf-8') if isinstance(self.invoice_pdf, bytes) else self.invoice_pdf
        
        prompt_text = """Vous êtes un assistant comptable. Lisez la facture PDF jointe et extrayez UNIQUEMENT les informations suivantes au format JSON :
1. "supplier" : Le nom du fournisseur (ex: "MARGLORY", "SUTRA", etc.)
2. "invoice_number" : Le numéro de la facture.
3. "invoice_date" : La date de la facture au format YYYY-MM-DD.

Répondez UNIQUEMENT avec du JSON valide, sans explication, sans markdown. 
Si une information manque, mettez null.

Exemple de réponse attendue :
{
    "supplier": "Nom du Fournisseur",
    "invoice_number": "FA-2024-001",
    "invoice_date": "2024-04-20"
}"""

        # Utilisation de l'API OpenAI (Format identique aux autres modules du repo)
        payload = {
            "model": "gpt-4o",
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": self.invoice_filename or "invoice.pdf",
                            "file_data": f"data:application/pdf;base64,{pdf_b64}"
                        },
                        {
                            "type": "input_text",
                            "text": prompt_text
                        }
                    ]
                }
            ],
            "text": {
                "format": {
                    "type": "json_object"
                }
            },
            "temperature": 0.0,
            "max_output_tokens": 500
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            # Note: v1/responses semble être un endpoint spécifique utilisé dans ce repo
            resp = requests.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            ai_data = resp.json()

            raw_content = ""
            for output_item in ai_data.get("output", []):
                for content_item in output_item.get("content", []):
                    if content_item.get("type") == "output_text":
                        raw_content = content_item.get("text", "")
                        break

            if not raw_content:
                raise ValidationError("L'IA n'a retourné aucune réponse. Vérifiez le fichier PDF.")

            result = json.loads(raw_content)

            # Mise à jour des champs
            vals = {}
            if result.get("supplier"):
                vals['supplier'] = result["supplier"]
            if result.get("invoice_number"):
                vals['invoice_number'] = result["invoice_number"]
            if result.get("invoice_date"):
                vals['invoice_date'] = result["invoice_date"]
                
            vals['state'] = 'extracted'
            self.write(vals)

            self.message_post(body=Markup(
                "<div style='color: green;'><i class='fa fa-check-circle'></i> <b>Extraction IA réussie</b></div>"
            ))

        except Exception as e:
            self.message_post(body=f"Erreur extraction IA : {str(e)}")
            raise ValidationError(f"Erreur lors de l'extraction IA : {str(e)}")
