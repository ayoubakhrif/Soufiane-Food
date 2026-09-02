import base64
import json
import logging
import requests
from odoo import http, SUPERUSER_ID, fields
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
            return {'status': 'error', 'message': '❌ *Erreur:* Accès non autorisé'}

        # 2. Extract data from request
        try:
            data = kwargs
            group_id = data.get('group_id', '')
            pdf_base64 = data.get('pdf_base64', '') or data.get('document_base64', '') or data.get('base64', '')
            file_name = data.get('file_name', 'document.pdf')
        except Exception as e:
            return {'status': 'error', 'message': f'❌ *Erreur JSON:* {str(e)}'}

        # 3. Security: Check Group ID
        PDF_GROUP_ID = '120363426857783962@g.us'
        if group_id != PDF_GROUP_ID:
            _logger.info(f"Ignoring request from group {group_id} in Finance PDF Agent")
            return {'status': 'ignored', 'message': 'Ce bot ne gère que le groupe Finance PDF.'}

        if not pdf_base64:
            _logger.info("No PDF found in the request. Ignoring.")
            return {'status': 'ignored', 'message': '❌ *Erreur:* Aucun document PDF fourni.'}

        # 4. Call OpenAI to extract invoices
        openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not openai_key:
            return {'status': 'error', 'message': '❌ *Erreur:* Clé API OpenAI non configurée (whatsapp_stock.openai_key)'}

        ai_result = self._extract_data_from_pdf(pdf_base64, file_name, openai_key)
        
        if not ai_result or 'error' in ai_result:
            return {'status': 'error', 'message': f"❌ *Erreur IA:* {ai_result.get('error', 'Erreur inconnue')}"}

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
                return {'status': 'error', 'message': f"❌ *Erreur IA (2e essai):* {ai_result.get('error', 'Erreur inconnue')}"}
            factures = ai_result.get('factures', [])

        chq_number = ai_result.get('chq_number', '')

        # Fallback: Extract from filename early if AI didn't find it
        if not chq_number and file_name:
            import re
            match = re.search(r'\b(\d{7})\b', file_name)
            if match:
                chq_number = match.group(1)

        if not chq_number:
            return {'status': 'error', 'message': "❌ *Erreur:* L'IA n'a pas pu identifier le numéro de chèque ni dans le PDF ni dans le nom du fichier (7 chiffres)."}
        
        if not factures:
            return {'status': 'error', 'message': "❌ *Erreur:* L'IA n'a pas trouvé de factures valides dans le PDF."}

        # 5. Find the DataCheque in reserve or bureau
        domain = [('chq', '=', chq_number), ('state', 'in', ['reserve', 'bureau'])]
        base_cheque = request.env['datacheque'].sudo().search(domain, order='id asc', limit=1)

        if not base_cheque:
            # Let's search if any cheque exists even if not in reserve to provide a better error
            existing = request.env['datacheque'].sudo().search([('chq', '=', chq_number)])
            if existing:
                return {'status': 'error', 'message': f"❌ *Erreur:* Le chèque {chq_number} existe mais n'est pas à l'état réserve ou bureau."}
            
            # Fallback: Try extracting 7 digits from the filename
            import re
            filename_chq = None
            if file_name:
                match = re.search(r'\b(\d{7})\b', file_name)
                if match:
                    filename_chq = match.group(1)
            
            if filename_chq and filename_chq != chq_number:
                chq_number = filename_chq
                domain = [('chq', '=', chq_number), ('state', 'in', ['reserve', 'bureau'])]
                base_cheque = request.env['datacheque'].sudo().search(domain, order='id asc', limit=1)
                
                if not base_cheque:
                    existing = request.env['datacheque'].sudo().search([('chq', '=', chq_number)])
                    if existing:
                        return {'status': 'error', 'message': f"❌ *Erreur:* Le chèque {chq_number} (trouvé dans le nom du fichier) existe mais n'est pas à l'état réserve ou bureau."}
                    return {'status': 'error', 'message': f"❌ *Erreur:* Les chèques {ai_result.get('chq_number', '')} et {chq_number} n'existent pas ou ne sont pas en attente (réserve/bureau)."}
            else:
                return {'status': 'error', 'message': f"❌ *Erreur:* Le chèque {chq_number} n'existe pas ou n'est pas en attente (réserve ou bureau)."}

        created_records = []
        messages = []

        try:
            for idx, inv_data in enumerate(factures):
                inv_amount = float(inv_data.get('montant', 0))
                inv_type = inv_data.get('type', 'divers').lower()
                inv_benif_name = inv_data.get('beneficiaire', '')
                inv_facture_num = str(inv_data.get('numero_facture', '')).strip()
                inv_bl = str(inv_data.get('bl', '')).strip()

                # Match Beneficiaire
                benif_record = False
                if inv_benif_name:
                    benif_record = request.env['finance.benif'].sudo().search([('name', 'ilike', inv_benif_name)], limit=1)

                # Force the type according to beneficiary rules
                if benif_record:
                    if benif_record.type == 'divers':
                        inv_type = 'divers'
                    elif benif_record.type == 'import' and inv_type == 'divers':
                        inv_type = 'magasinage' # fallback for import so it doesn't stay 'divers'

                if inv_type not in ['magasinage', 'surestarie', 'change', 'fret', 'thc', 'divers', 'inspection']:
                    inv_type = 'divers'

                # Prepare values
                vals = {
                    'amount': inv_amount,
                    'type': inv_type,
                    'journal': base_cheque.journal,
                    'state': 'reserve',
                }

                if base_cheque.state == 'bureau' or not base_cheque.date_emission:
                    vals['date_emission'] = fields.Date.context_today(base_cheque)
                if base_cheque.state == 'bureau' or not base_cheque.date_echeance:
                    vals['date_echeance'] = fields.Date.context_today(base_cheque)

                if benif_record:
                    vals['benif_id'] = benif_record.id

                if inv_facture_num and inv_facture_num.lower() != 'none':
                    vals['facture'] = 'fact'
                    vals['serie'] = inv_facture_num[:100]
                else:
                    vals['facture'] = 'm'
                    vals['serie'] = False
                    
                if inv_bl and inv_bl.lower() != 'none':
                    vals['bl'] = inv_bl[:100]

                bl_str = f", BL: {vals['bl']}" if vals.get('bl') else ""
                fact_str = f", Fact: {vals['serie']}" if vals.get('serie') else ""

                if idx == 0:
                    # Update base cheque
                    base_cheque.write(vals)
                    created_records.append(base_cheque)
                    messages.append(f"• {inv_amount} DH ({vals['type']}) pour {benif_record.name if benif_record else inv_benif_name}{bl_str}{fact_str}")
                    
                    # Log AI Training
                    request.env['finance.ai.training'].sudo().create({
                        'source': 'whatsapp',
                        'prompt_text': ai_result.get('_prompt', ''),
                        'ai_result_json': ai_result.get('_raw_json', ''),
                        'final_result_json': ai_result.get('_raw_json', ''),
                        'datacheque_id': base_cheque.id,
                    })
                else:
                    # Duplicate cheque for the remaining invoices
                    new_cheque = base_cheque.copy(default=vals)
                    created_records.append(new_cheque)
                    messages.append(f"• {inv_amount} DH ({vals['type']}) pour {benif_record.name if benif_record else inv_benif_name}{bl_str}{fact_str}")
                    
                    # Log AI Training
                    request.env['finance.ai.training'].sudo().create({
                        'source': 'whatsapp',
                        'prompt_text': ai_result.get('_prompt', ''),
                        'ai_result_json': ai_result.get('_raw_json', ''),
                        'final_result_json': ai_result.get('_raw_json', ''),
                        'datacheque_id': new_cheque.id,
                    })
            
            return {
                'status': 'success',
                'response': f"✅ *PDF traité avec succès !*\n\n*Chèque N°:* {chq_number}\n\n*Répartitions saisies :*\n" + "\n".join(messages)
            }
        except Exception as e:
            _logger.error(f"Error updating/creating datacheques from PDF: {str(e)}")
            return {'status': 'error', 'message': f"❌ *Erreur serveur:* {str(e)}"}

    def _extract_data_from_pdf(self, pdf_b64, file_name, api_key, feedback=None):
        """Use OpenAI to extract cheque and invoice data from PDF."""
        # Get beneficiary lists to guide the AI
        import_benifs = request.env['finance.benif'].sudo().search([('type', '=', 'import')]).mapped('name')
        divers_benifs = request.env['finance.benif'].sudo().search([('type', '=', 'divers')]).mapped('name')
        
        import_list_str = ", ".join(import_benifs) if import_benifs else "Aucun"
        divers_list_str = ", ".join(divers_benifs) if divers_benifs else "Aucun"

        feedback_instruction = f"\n\nATTENTION ERREUR PRÉCÉDENTE À CORRIGER :\n{feedback}\nVeuillez revérifier et corriger le 'type' pour ces factures." if feedback else ""

        prompt_text = """Vous êtes un assistant comptable spécialisé dans l'importation et la finance. Vous recevez un document (PDF) qui contient généralement un chèque et une ou plusieurs factures.
Votre but est d'analyser le document et d'extraire les informations nécessaires pour l'ERP Odoo.

1. Trouvez le numéro de chèque. ATTENTION RÈGLE ABSOLUE : Le chèque se trouve TOUJOURS sur la dernière page du document. Le numéro de chèque est EXACTEMENT composé de 7 chiffres et se trouve TOUJOURS en haut à gauche du chèque (souvent après la mention 'Chèque N°' ou 'N.'). Il ne fait jamais plus de 7 chiffres. Ne le confondez SURTOUT PAS avec les numéros de compte très longs en bas, ni avec le montant du chèque qui se trouve TOUJOURS en haut à droite. S'il y a plusieurs factures ou plusieurs types de frais dans le même document, traitez-les séparément.
   (NOTE SPÉCIALE CMA ET HMM : Pour les bénéficiaires "CMA" et "HMM", les frais de "magasinage" et de "surestarie" apparaissent souvent sur la MÊME facture. De plus, les montants en haut sont souvent affichés en HT, et la TVA se trouve tout en bas de la facture. Vous DEVEZ OBLIGATOIREMENT suivre ces règles de calcul pour extraire les montants TTC :
   - Le montant TTC du "magasinage" est la SOMME EXACTE de tous les montants HT qui se trouvent sous le titre "(L) Terminal full storage at destination" + le montant de la TVA associée en bas (qui commence par "L TVA"). De plus, INCLUEZ AUSSI la "Taxe Regionale" dans le magasinage (même si elle se trouve sous "Charges Diverses").
   - Le montant TTC de la "surestarie" est la SOMME EXACTE de tous les montants HT qui se trouvent sous le titre "(C) Detention & Demurrage Import Charge" + le montant de la TVA associée en bas (qui commence par "C TVA").
   Extrayez ces deux totaux calculés en TTC comme DEUX éléments séparés dans votre tableau JSON, l'un avec le type "magasinage" et l'autre avec le type "surestarie").
2. Pour chaque facture (ou ligne de frais séparée), extrayez :
   - Le montant TTC (numérique).
   - Le bénéficiaire ou fournisseur.
   - Le numéro de la facture (UNIQUEMENT le numéro exact, sans le préfixe F/ ou Facture. Cherchez les numéros isolés en haut comme TI-...). S'il n'y en a pas, mettez une chaine vide "". (Note importante: pour le bénéficiaire CMA, la facture commence souvent par MAMI).
   - Le BL (Bill of Lading, Connaissement maritime, ex: YMJAM450339005). Cherchez "BL", "B/L", ou une longue référence alphanumérique liée au navire/conteneur. S'il n'y en a pas, mettez une chaine vide "".
   - Le "type" de frais. 

Règles strictes pour le "type" de frais :
- Si la facture indique (Magasinage, Magasinage Eurogate, Terminal storage, taxe regional) -> VOUS DEVEZ ABSOLUMENT choisir "magasinage".
- Si la facture indique (Surestarie, Free det, detention, demurage fee, demurage...) -> choisissez "surestarie".
- Si la facture indique (THC, Droit de port, Frais d'agence, Frais de port, agency fee, frais de manutention...) -> choisissez "thc".
- PRIORITÉ: Si le mot "MAGASINAGE" apparait, c'est obligatoirement "magasinage".

- Voici la liste des bénéficiaires de type IMPORTATION : [IMPORT_LIST]. Si le bénéficiaire correspond à l'un de ces noms (ou s'il s'agit d'un acteur maritime/portuaire/douanier), vous NE DEVEZ JAMAIS choisir "divers". Vous devez OBLIGATOIREMENT choisir l'un de ces types : "magasinage", "surestarie", "thc", "inspection", "change", ou "fret".
- Voici la liste des bénéficiaires de type DIVERS : [DIVERS_LIST]. Si le bénéficiaire correspond à l'un de ces noms, vous DEVEZ OBLIGATOIREMENT choisir "divers".[FEEDBACK]

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
      "numero_facture": "2023-001",
      "bl": "YMJAM450339005"
    }
  ]
}
"""
        
        prompt_text = prompt_text.replace("[IMPORT_LIST]", import_list_str)
        prompt_text = prompt_text.replace("[DIVERS_LIST]", divers_list_str)
        prompt_text = prompt_text.replace("[FEEDBACK]", feedback_instruction)
        
        import base64
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return {'error': "PyMuPDF (fitz) n'est pas installé sur le serveur pour lire le PDF vers OpenAI."}
            
        pdf_bytes = base64.b64decode(pdf_b64)
        
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            content_array = [
                {"type": "text", "text": prompt_text}
            ]
            
            # Limit to first 6 pages to avoid token explosion
            for page_num in range(min(6, len(doc))):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("jpeg")
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                content_array.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_b64}",
                        "detail": "high"
                    }
                })
        except Exception as e:
            return {'error': f"Erreur lors de la conversion du PDF en images : {str(e)}"}

        url = "https://api.openai.com/v1/chat/completions"

        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": content_array
                }
            ],
            "response_format": { "type": "json_object" },
            "temperature": 0.0,
            "max_tokens": 2048
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            ai_data = resp.json()

            raw_content = ""
            choices = ai_data.get("choices", [])
            if choices and choices[0].get("message", {}).get("content"):
                raw_content = choices[0]["message"]["content"]

            if not raw_content:
                return {'error': "L'IA OpenAI n'a retourné aucune réponse."}

            # The response is expected to be JSON string
            import re
            
            raw_content = raw_content.strip()
            
            # Robust JSON extraction: look for json code block first
            json_match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", raw_content, re.DOTALL)
            if json_match:
                raw_content = json_match.group(1).strip()
            else:
                # If no markdown block, try to find the first { or [ and last } or ]
                start_idx = raw_content.find('{')
                start_arr_idx = raw_content.find('[')
                
                valid_starts = [i for i in (start_idx, start_arr_idx) if i != -1]
                if valid_starts:
                    start = min(valid_starts)
                    end_char = '}' if start == start_idx else ']'
                    end = raw_content.rfind(end_char)
                    if end != -1 and end > start:
                        raw_content = raw_content[start:end+1]
                        
            try:
                result = json.loads(raw_content)
            except Exception as e:
                # Fallback: maybe it's truncated? Try to append '}' just in case
                if raw_content.endswith(']'):
                    try:
                        result = json.loads(raw_content + '}')
                    except Exception:
                        return {'error': f"Erreur de parsing JSON: {str(e)}\n\nTexte brut:\n{raw_content}"}
                else:
                    return {'error': f"Erreur de parsing JSON: {str(e)}\n\nTexte brut:\n{raw_content}"}
                
            if isinstance(result, list):
                if len(result) > 0 and isinstance(result[0], dict):
                    result = result[0]
                else:
                    result = {}
            elif not isinstance(result, dict):
                result = {}

            result['_raw_json'] = raw_content
            result['_prompt'] = prompt_text
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
