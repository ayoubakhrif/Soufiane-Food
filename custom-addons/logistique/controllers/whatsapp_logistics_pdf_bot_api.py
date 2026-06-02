import base64
import json
import logging
import requests
from odoo import http, SUPERUSER_ID, fields
from odoo.http import request
from datetime import datetime

_logger = logging.getLogger(__name__)

class WhatsAppLogisticsPdfController(http.Controller):

    @http.route('/api/whatsapp/logistique/pdf', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_logistics_pdf_processor(self, **kwargs):
        # Force database
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        # 1. Verification of API Key
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'whatsapp_direct_quantity')
        
        if not api_key or api_key != expected_api_key:
            _logger.warning("Unauthorized access attempt to WhatsApp Logistics PDF API")
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
        LOGISTICS_PDF_GROUP_ID = '120363428159815503@g.us'
        if group_id != LOGISTICS_PDF_GROUP_ID:
            _logger.info(f"Ignoring request from group {group_id} in Logistics PDF Agent")
            return {'status': 'ignored', 'message': 'This agent only handles the Logistics PDF Group.'}

        if not pdf_base64:
            _logger.info("No PDF found in the request. Ignoring.")
            return {'status': 'ignored', 'message': 'No PDF document provided.'}

        # 4. Call OpenAI to extract invoices, BAD date and BL
        openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not openai_key:
            return {'status': 'error', 'message': 'OpenAI API key not configured'}

        ai_result = self._extract_data_from_pdf(pdf_base64, file_name, openai_key)
        
        if not ai_result or 'error' in ai_result:
            return {'status': 'error', 'message': f"Erreur IA: {ai_result.get('error', 'Erreur inconnue')}"}

        factures = ai_result.get('factures', [])
        chq_number = ai_result.get('chq_number', '')
        bl_number = ai_result.get('bl_number', '')
        bad_date_str = ai_result.get('bad_date', '')

        if not bl_number:
            return {'status': 'error', 'message': "L'IA n'a pas pu identifier le numéro de BL dans le PDF. La recherche du dossier est impossible."}
        
        # Format BL Number to match logic in entry
        bl_number = str(bl_number).strip().upper()

        # 5. Find Dossier and Entry
        # Search by BL Number on logistique.dossier
        dossier = request.env['logistique.dossier'].sudo().search([('name', '=ilike', bl_number)], limit=1)
        
        if not dossier:
             return {'status': 'error', 'message': f"Aucun dossier trouvé pour le BL: {bl_number}."}

        entry = request.env['logistique.entry'].sudo().search([('dossier_id', '=', dossier.id)], limit=1)
        
        if not entry:
            return {'status': 'error', 'message': f"Aucune entrée logistique trouvée pour le dossier BL: {bl_number}."}

        messages = []
        messages.append(f"✅ Dossier identifié : {dossier.name}")

        # 6. Update BAD Date
        if bad_date_str and bad_date_str.lower() != 'none':
            try:
                # the AI is instructed to return YYYY-MM-DD
                bad_date_obj = datetime.strptime(bad_date_str, '%Y-%m-%d').date()
                entry.write({'bad_date': bad_date_obj})
                messages.append(f"📅 Date de BAD mise à jour : {bad_date_str}")
            except Exception as e:
                messages.append(f"⚠️ Impossible de parser la date de BAD extraite ({bad_date_str}): {str(e)}")

        if not chq_number:
            messages.append("⚠️ Aucun numéro de chèque identifié dans le document.")
        elif not factures:
            messages.append("⚠️ Aucune facture identifiée dans le document à répartir.")
        else:
            # 7. Create Cheque Divisions
            messages.append(f"🧾 Traitement du chèque N° {chq_number}")
            
            # Check if any divisions for this cheque already exist in the dossier (optional protection)
            existing_cheques = request.env['logistique.dossier.cheque'].sudo().search([
                ('dossier_id', '=', dossier.id),
                ('cheque_serie', '=', chq_number)
            ])
            
            if existing_cheques:
                messages.append(f"ℹ️ Le chèque {chq_number} est déjà réparti dans ce dossier. Nouvelles lignes ajoutées.")

            for idx, inv_data in enumerate(factures):
                inv_amount = float(inv_data.get('montant', 0))
                inv_type = inv_data.get('type', 'autres').lower()
                inv_benif_name = inv_data.get('beneficiaire', '')

                # Match Beneficiary in logistique.shipping
                benif_record = False
                if inv_benif_name:
                    benif_record = request.env['logistique.shipping'].sudo().search([('name', 'ilike', inv_benif_name)], limit=1)

                if inv_type not in ['thc', 'magasinage', 'fret', 'surestarie', 'autres']:
                    inv_type = 'autres'

                # Prepare values
                vals = {
                    'cheque_serie': chq_number,
                    'amount': inv_amount,
                    'type': inv_type,
                    'dossier_id': dossier.id,
                    'entry_id': entry.id,
                    'ste_id': dossier.ste_id.id if dossier.ste_id else False,
                    'date': fields.Date.today()
                }

                if benif_record:
                    vals['beneficiary_id'] = benif_record.id

                try:
                    request.env['logistique.dossier.cheque'].sudo().create(vals)
                    benif_display = benif_record.name if benif_record else inv_benif_name
                    messages.append(f"➕ Répartition créée : {inv_amount} DH (Type: {vals['type']}, Bénéficiaire: {benif_display})")
                except Exception as e:
                    messages.append(f"❌ Erreur création répartition {inv_amount} DH : {str(e)}")
            
        return {
            'status': 'success',
            'message': "Traitement logistique réussi.",
            'details': "\n".join(messages)
        }

    def _extract_data_from_pdf(self, pdf_b64, file_name, api_key):
        """Use OpenAI to extract cheque, invoices and BAD data from PDF."""
        # Get shipping lists to guide the AI for beneficiaries
        shippings = request.env['logistique.shipping'].sudo().search([]).mapped('name')
        shipping_list_str = ", ".join(shippings) if shippings else "Aucun"

        prompt_text = """Vous êtes un assistant logistique. Vous recevez un document (PDF) qui contient généralement un chèque, une ou plusieurs factures, et parfois un Bon à Délivrer (BAD).
Votre but est d'analyser le document et d'extraire les informations nécessaires pour l'ERP Odoo.

1. Trouvez le numéro de chèque (généralement 7 chiffres consécutifs). S'il n'y en a pas, mettez une chaîne vide "".
2. Trouvez le numéro de BL (Bill of Lading, Connaissement maritime, ex: YMJAM450339005). Cherchez "BL", "B/L", ou une longue référence alphanumérique liée au navire/conteneur. Obligatoire.
3. Trouvez la date du BAD (Bon à Délivrer). Si vous trouvez une date associée au BAD, retournez-la au format YYYY-MM-DD. Sinon, "".
4. Pour chaque facture (ou ligne de frais séparée) associée, extrayez :
   - Le montant TTC (numérique).
   - Le bénéficiaire ou fournisseur. Voici la liste des compagnies maritimes connues : [SHIPPING_LIST]. Essayez de mapper le bénéficiaire à l'un de ces noms.
   - Le "type" de frais.

Règles strictes pour le "type" de frais :
- Si la facture indique (Magasinage, Magasinage Eurogate, Terminal storage, taxe regional) -> VOUS DEVEZ ABSOLUMENT choisir "magasinage".
- Si la facture indique (Surestarie, Free det, detention, demurage fee, demurage...) -> choisissez "surestarie".
- Si la facture indique (THC, Droit de port, Frais d'agence, Frais de port, agency fee, frais de manutention...) -> choisissez "thc".
- Si la facture indique (Fret, Freight, Sea Freight...) -> choisissez "fret".
- PRIORITÉ: Si le mot "MAGASINAGE" apparait, c'est obligatoirement "magasinage".
- Si aucun de ces types ne correspond, mettez "autres".

Règles de formatage :
- Retournez UNIQUEMENT un objet JSON valide, sans formatage markdown, sans explications.
- Le JSON doit suivre cette structure exacte :
{
  "chq_number": "1234567",
  "bl_number": "YMJAM450339005",
  "bad_date": "2023-10-15",
  "factures": [
    {
      "montant": 10500.50,
      "beneficiaire": "Tanger Med",
      "type": "magasinage",
      "numero_facture": "2023-001"
    }
  ]
}
"""
        
        prompt_text = prompt_text.replace("[SHIPPING_LIST]", shipping_list_str)
        
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
