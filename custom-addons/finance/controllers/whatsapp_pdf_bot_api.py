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

        factures = ai_result.get('factures', [])

        # Retry logic if IA assigned 'divers' to an import beneficiary
        needs_retry = False
        feedback_msgs = []
        for inv in factures:
            inv_type = inv.get('type', 'divers').lower()
            inv_benif_name = inv.get('beneficiaire', '')
            if inv_type == 'divers' and inv_benif_name:
                benif_record = request.env['finance.benif'].sudo().search([('name', 'ilike', inv_benif_name)], limit=1)
                if benif_record and benif_record.type == 'import':
                    needs_retry = True
                    feedback_msgs.append(f"Vous avez classé {inv_benif_name} comme 'divers' mais c'est un fournisseur d'importation. Le type doit être magasinage, surestarie, thc, change ou fret, JAMAIS divers.")
        
        if needs_retry:
            _logger.info("Retrying AI extraction because of 'divers' assigned to 'import' benif")
            ai_result = self._extract_data_from_pdf(pdf_base64, file_name, openai_key, feedback="\n".join(feedback_msgs))
            if not ai_result or 'error' in ai_result:
                return {'status': 'error', 'message': f"Erreur IA lors du 2e essai: {ai_result.get('error', 'Erreur inconnue')}"}
            factures = ai_result.get('factures', [])

        chq_number = ai_result.get('chq_number', '')

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
            # Aggregate factures by type to avoid duplicate (chq, ste_id, type) constraints
            aggregated_factures = {}
            for inv in factures:
                inv_type = inv.get('type', 'divers').lower()
                inv_benif_name = inv.get('beneficiaire', '')

                # Force the type according to beneficiary rules
                benif_record = False
                if inv_benif_name:
                    benif_record = request.env['finance.benif'].sudo().search([('name', 'ilike', inv_benif_name)], limit=1)

                if benif_record:
                    if benif_record.type == 'divers':
                        inv_type = 'divers'
                    elif benif_record.type == 'import' and inv_type == 'divers':
                        inv_type = 'magasinage' # fallback for import so it doesn't stay 'divers'

                if inv_type not in ['magasinage', 'surestarie', 'change', 'fret', 'thc', 'divers', 'inspection']:
                    inv_type = 'divers'
                    
                if inv_type not in aggregated_factures:
                    aggregated_factures[inv_type] = {
                        'type': inv_type,
                        'montant': 0.0,
                        'beneficiaire': inv_benif_name,
                        'numero_facture': []
                    }
                
                aggregated_factures[inv_type]['montant'] += float(inv.get('montant', 0))
                num = str(inv.get('numero_facture', '')).strip()
                if num and num.lower() != 'none':
                    if num not in aggregated_factures[inv_type]['numero_facture']:
                        aggregated_factures[inv_type]['numero_facture'].append(num)

            for idx, inv_data in enumerate(aggregated_factures.values()):
                inv_amount = inv_data['montant']
                inv_type = inv_data['type']
                inv_benif_name = inv_data['beneficiaire']
                inv_facture_nums = inv_data['numero_facture']

                # Match Beneficiaire again for ID
                benif_record = False
                if inv_benif_name:
                    benif_record = request.env['finance.benif'].sudo().search([('name', 'ilike', inv_benif_name)], limit=1)

                # Prepare values
                vals = {
                    'amount': inv_amount,
                    'type': inv_type,
                }

                if benif_record:
                    vals['benif_id'] = benif_record.id

                if inv_facture_nums:
                    vals['facture'] = 'fact'
                    # Join multiple invoice numbers
                    vals['serie'] = ", ".join(inv_facture_nums)[:100]
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

    def _extract_data_from_pdf(self, pdf_b64, file_name, api_key, feedback=None):
        """Use OpenAI to extract cheque and invoice data from PDF."""
        # Get beneficiary lists to guide the AI
        import_benifs = request.env['finance.benif'].sudo().search([('type', '=', 'import')]).mapped('name')
        divers_benifs = request.env['finance.benif'].sudo().search([('type', '=', 'divers')]).mapped('name')
        
        import_list_str = ", ".join(import_benifs) if import_benifs else "Aucun"
        divers_list_str = ", ".join(divers_benifs) if divers_benifs else "Aucun"

        feedback_instruction = f"\n\nATTENTION ERREUR PRÉCÉDENTE À CORRIGER :\n{feedback}\nVeuillez revérifier et corriger le 'type' pour ces factures." if feedback else ""

        prompt_text = f"""Vous êtes un assistant comptable spécialisé dans l'importation et la finance. Vous recevez un document (PDF) qui contient généralement un chèque et une ou plusieurs factures.
Votre but est d'analyser le document et d'extraire les informations nécessaires pour l'ERP Odoo.

1. Trouvez le numéro de chèque (généralement 7 chiffres consécutifs).
2. Pour chaque facture, extrayez :
   - Le montant TTC (numérique).
   - Le bénéficiaire ou fournisseur.
   - Le numéro de la facture (UNIQUEMENT le numéro exact de la facture, sans le préfixe F/ ou Facture). S'il n'y en a pas, mettez une chaine vide "".
   - Le "type" de frais. 

Règles strictes pour le "type" de frais :
- Si la facture indique (Droit de port, Frais d'agence, Frais de port, agency fee, frais de manutention...) -> choisissez "thc"
- Si la facture indique (Free det, detention, demurage fee, demurage...) -> choisissez "surestarie"
- Si la facture indique (Terminal storage, taxe regional) -> choisissez "magasinage"

- Voici la liste des bénéficiaires de type IMPORTATION : {import_list_str}. Si le bénéficiaire correspond à l'un de ces noms (ou s'il s'agit d'un acteur maritime/portuaire/douanier), vous NE DEVEZ JAMAIS choisir "divers". Vous devez OBLIGATOIREMENT choisir l'un de ces types : "magasinage", "surestarie", "thc", "inspection", "change", ou "fret".
- Voici la liste des bénéficiaires de type DIVERS : {divers_list_str}. Si le bénéficiaire correspond à l'un de ces noms, vous DEVEZ OBLIGATOIREMENT choisir "divers".{feedback_instruction}

Règles de formatage :
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
