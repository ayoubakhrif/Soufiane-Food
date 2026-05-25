import base64
import json
import logging
import requests
from odoo import http, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppFinancePdfController(http.Controller):

    @http.route('/api/whatsapp/finance/pdf', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_finance_pdf_processor(self, **kwargs):
        # Force database
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        # 1. Verification of API Key
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'whatsapp_direct_quantity')
        
        if not api_key or api_key != expected_api_key:
            _logger.warning("Unauthorized access attempt to WhatsApp Finance PDF API")
            return {'status': 'error', 'message': 'Unauthorized'}

        # 2. Extract data from request
        try:
            data = kwargs
            group_id = data.get('group_id', '')
            pdf_base64 = data.get('pdf_base64', '') or data.get('document_base64', '') or data.get('base64', '')
            file_name = data.get('file_name', 'document.pdf')
        except Exception as e:
            return {'status': 'error', 'message': f'Invalid JSON: {str(e)}'}

        # 3. Security: Check Group ID
        PDF_GROUP_ID = '120363426857783962@g.us'
        if group_id != PDF_GROUP_ID:
            _logger.info(f"Ignoring request from group {group_id} in Finance PDF Agent")
            return {'status': 'ignored', 'message': 'This agent only handles the Finance PDF Group.'}

        if not pdf_base64:
            _logger.info("No PDF found in the request. Ignoring.")
            return {'status': 'ignored', 'message': 'No PDF document provided.'}

        # 4. Call OpenAI to extract invoices
        openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not openai_key:
            return {'status': 'error', 'message': 'OpenAI API key not configured'}

        ai_result = self._extract_data_from_pdf(pdf_base64, file_name, openai_key)
        
        if not ai_result or 'error' in ai_result:
            return {'status': 'error', 'message': f"Erreur IA: {ai_result.get('error', 'Erreur inconnue')}"}

        chq_number = ai_result.get('chq_number', '')
        factures = ai_result.get('factures', [])

        if not chq_number:
            return {'status': 'error', 'message': "L'IA n'a pas pu identifier le numéro de chèque dans le PDF."}
        
        if not factures:
            return {'status': 'error', 'message': "L'IA n'a pas trouvé de factures valides dans le PDF."}

        # 5. Find the DataCheque in reserve
        domain = [('chq', '=', chq_number), ('state', '=', 'reserve')]
        base_cheque = request.env['datacheque'].sudo().search(domain, order='id asc', limit=1)

        if not base_cheque:
            # Let's search if any cheque exists even if not in reserve to provide a better error
            existing = request.env['datacheque'].sudo().search([('chq', '=', chq_number)])
            if existing:
                return {'status': 'error', 'message': f"Le chèque {chq_number} existe mais n'est pas à l'état réserve."}
            return {'status': 'error', 'message': f"Le chèque {chq_number} n'existe pas."}

        created_records = []
        messages = []

        try:
            for idx, inv in enumerate(factures):
                inv_amount = float(inv.get('montant', 0))
                inv_type = inv.get('type', 'divers').lower()
                inv_facture_num = str(inv.get('numero_facture', '')).strip()
                inv_benif_name = inv.get('beneficiaire', '')

                # Match Beneficiaire
                benif_record = False
                if inv_benif_name:
                    benif_record = request.env['finance.benif'].sudo().search([('name', 'ilike', inv_benif_name)], limit=1)

                # Prepare values
                vals = {
                    'amount': inv_amount,
                    'type': inv_type if inv_type in ['magasinage', 'surestarie', 'change', 'fret', 'divers', 'inspection'] else 'divers',
                }

                if benif_record:
                    vals['benif_id'] = benif_record.id

                if inv_facture_num and inv_facture_num.lower() != 'none':
                    vals['facture'] = 'fact'
                    vals['serie'] = inv_facture_num
                else:
                    vals['facture'] = 'm'
                    vals['serie'] = False

                if idx == 0:
                    # Update base cheque
                    base_cheque.write(vals)
                    created_records.append(base_cheque)
                    messages.append(f"Mise à jour du chèque {chq_number} : {inv_amount} DH (Type: {vals['type']})")
                else:
                    # Duplicate cheque for the remaining invoices
                    # Since base_cheque has ste_id, perso_id, journal, etc. these will be copied
                    new_cheque = base_cheque.copy(default=vals)
                    created_records.append(new_cheque)
                    messages.append(f"Création d'une répartition pour {chq_number} : {inv_amount} DH (Type: {vals['type']})")
            
            return {
                'status': 'success',
                'message': "Traitement réussi.",
                'details': "\n".join(messages)
            }
        except Exception as e:
            _logger.error(f"Error updating/creating datacheques from PDF: {str(e)}")
            return {'status': 'error', 'message': f"Erreur lors de la mise à jour des chèques: {str(e)}"}

    def _extract_data_from_pdf(self, pdf_b64, file_name, api_key):
        """Use OpenAI to extract cheque and invoice data from PDF."""
        prompt_text = """Vous êtes un assistant comptable spécialisé dans l'importation et la finance. Vous recevez un document (PDF) qui contient généralement un chèque et une ou plusieurs factures.
Votre but est d'analyser le document et d'extraire les informations nécessaires pour l'ERP Odoo.

1. Trouvez le numéro de chèque (généralement 7 chiffres consécutifs).
2. Pour chaque facture, extrayez :
   - Le montant TTC (numérique).
   - Le bénéficiaire ou fournisseur.
   - Le numéro de la facture. S'il n'y en a pas, mettez une chaine vide "".
   - Le "type" de frais. Si le document concerne de l'importation (droits de douane, port, etc.), choisissez parmi : "magasinage", "surestarie", ou "inspection". Sinon, si c'est un autre type de prestation, choisissez "divers".

Règles strictes :
- Retournez UNIQUEMENT un objet JSON valide, sans formatage markdown, sans explications.
- Le JSON doit suivre cette structure exacte :
{
  "chq_number": "1234567",
  "factures": [
    {
      "montant": 10500.50,
      "beneficiaire": "Tanger Med",
      "type": "magasinage",
      "numero_facture": "F-2023-001"
    }
  ]
}
"""
        
        payload = {
            "model": "gpt-4o",
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": file_name,
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
            "max_output_tokens": 1000
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            ai_data = resp.json()

            raw_content = ""
            for output_item in ai_data.get("output", []):
                for content_item in output_item.get("content", []):
                    if content_item.get("type") == "output_text":
                        raw_content = content_item.get("text", "")
                        break

            if not raw_content:
                return {'error': "L'IA n'a retourné aucune réponse."}

            # The response is expected to be JSON string
            result = json.loads(raw_content)
            return result

        except requests.exceptions.HTTPError as e:
            err_body = ""
            try:
                err_body = e.response.json().get("error", {}).get("message", "")
            except Exception:
                pass
            return {'error': f"HTTP {e.response.status_code} : {err_body or str(e)}"}
        except Exception as e:
            return {'error': str(e)}
