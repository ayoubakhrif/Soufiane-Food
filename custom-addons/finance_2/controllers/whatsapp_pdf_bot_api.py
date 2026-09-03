import base64
import json
import logging
import requests
from odoo import http, SUPERUSER_ID, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppFinancePdfController(http.Controller):

    @http.route('/api/whatsapp/finance2/pdf', type='json', auth='none', methods=['POST'], csrf=False)
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

        # 5. Find the Cheque in finance_2
        chq_ste_ai = ai_result.get('chq_ste', '')
        
        domain = [('name', '=', chq_number)]
        base_cheques = request.env['finance2.cheque'].sudo().search(domain)
        
        base_cheque = False
        if base_cheques:
            # S'il y a un seul chèque, on le prend directement sans se casser la tête
            if len(base_cheques) == 1:
                base_cheque = base_cheques[0]
            else:
                # S'il y a plusieurs chèques, on essaie de filtrer par la société trouvée par l'IA
                filtered_cheques = base_cheques
                if chq_ste_ai:
                    # On vérifie dans la raison sociale ou dans le nom (l'abréviation)
                    matched = base_cheques.filtered(lambda c: 
                        (c.ste_id.raison_social and chq_ste_ai.lower() in c.ste_id.raison_social.lower()) or 
                        (c.ste_id.name and chq_ste_ai.lower() in c.ste_id.name.lower())
                    )
                    if matched:
                        filtered_cheques = matched
                        
                # Parmi les chèques filtrés (ou tous s'il n'y a pas de match de société), on priorise 'actif'
                actifs = filtered_cheques.filtered(lambda c: c.state == 'actif')
                if actifs:
                    base_cheque = actifs[0]
                else:
                    base_cheque = filtered_cheques[0]

        if not base_cheque:
            return {'status': 'error', 'message': f"❌ *Erreur:* Le chèque {chq_number} n'existe pas dans Odoo. Vous devez d'abord créer le chèque vide."}
            
        if base_cheque.state != 'actif':
            return {'status': 'error', 'message': f"❌ *Erreur:* Le chèque {chq_number} a été trouvé mais il est à l'état '{base_cheque.state}'. Il doit être à l'état 'actif' pour pouvoir recevoir des répartitions."}

        if base_cheque.repartition_ids:
            return {'status': 'error', 'message': f"❌ *Erreur:* Ce chèque ({chq_number}) a déjà des répartitions sur Gestia."}

        # Save the document PDF and the extracted cheque details
        update_vals = {}
        if pdf_base64:
            update_vals.update({
                'doc_pdf': pdf_base64,
                'doc_filename': file_name
            })
            
        chq_amount = ai_result.get('chq_amount')
        chq_date = ai_result.get('chq_date')
        
        if chq_amount:
            try:
                update_vals['amount_total'] = float(chq_amount)
            except ValueError:
                pass
                
        if chq_date and len(str(chq_date)) >= 10:
            update_vals['date_echeance'] = str(chq_date)[:10]

        if update_vals:
            base_cheque.sudo().write(update_vals)

        messages = []
        try:
            for idx, inv_data in enumerate(factures):
                inv_amount = float(inv_data.get('montant', 0))
                inv_facture_num = str(inv_data.get('numero_facture', '')).strip()
                inv_bl = str(inv_data.get('bl', '')).strip()
                inv_type = inv_data.get('type', '').lower()

                if inv_facture_num.lower() == 'none':
                    inv_facture_num = ''
                if inv_bl.lower() == 'none':
                    inv_bl = ''

                # Map AI type to Odoo selection
                type_val = False
                if inv_type in ['surestarie', 'magasinage', 'change', 'inspection']:
                    type_val = inv_type
                elif inv_type == 'thc':
                    type_val = 'change' # THC is basically change/port fees for them? Or maybe they didn't specify. I will let 'change' be used for THC if needed, but actually the user said: "change (THC)". So THC -> change.
                    
                # Create Repartition
                request.env['finance2.repartition'].sudo().create({
                    'cheque_id': base_cheque.id,
                    'amount': inv_amount,
                    'serie_facture': inv_facture_num,
                    'bl': inv_bl,
                    'type': type_val,
                })

                bl_str = f", BL: {inv_bl}" if inv_bl else ""
                fact_str = f", Fact: {inv_facture_num}" if inv_facture_num else ""
                type_str = f" ({type_val})" if type_val else ""
                messages.append(f"• {inv_amount} DH{type_str} {bl_str}{fact_str}")

            return {
                'status': 'success',
                'response': f"✅ *PDF traité avec succès (Finance V2) !*\n\n*Chèque N°:* {chq_number}\n\n*Répartitions ajoutées :*\n" + "\n".join(messages)
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

1. Trouvez les informations du chèque (qui se trouve TOUJOURS sur la dernière page du document) :
   - Le numéro de chèque: EXACTEMENT 7 chiffres, TOUJOURS en haut à gauche. Ne le confondez pas avec le compte ou le montant.
   - La société du chèque: Cherchez et extrayez la raison sociale exacte inscrite sur le chèque (ex: SOUFIANE NEGOCE, GENERALE...).
   - Le montant du chèque: C'est le montant total écrit sur le chèque (en haut à droite et en toutes lettres).
   - La date d'échéance du chèque: C'est la date écrite sur le chèque (souvent en bas à droite). Formatez-la OBLIGATOIREMENT en 'YYYY-MM-DD' (ex: 2026-08-15). S'il n'y a pas de date, laissez vide.
   (NOTE SPÉCIALE CMA ET HMM : 
   - Pour les bénéficiaires "CMA" et "HMM", la "Taxe Regionale" (même sous "Charges Diverses") DOIT TOUJOURS être comptée comme "magasinage".
   - RÈGLE DE CALCUL DE LA TVA EXCLUSIVE À CMA : Pour "CMA" UNIQUEMENT, les montants en haut sont souvent affichés en HT, et la TVA se trouve tout en bas. Vous DEVEZ suivre ces règles pour extraire les montants TTC :
      * Le montant TTC du "magasinage" = SOMME des montants HT sous "(L) Terminal full storage at destination" + le montant de la TVA en bas (commençant par "L TVA") + la "Taxe Regionale".
      * Le montant TTC de la "surestarie" = SOMME des montants HT sous "(C) Detention & Demurrage Import Charge" + le montant de la TVA en bas (commençant par "C TVA").
   - Pour les autres bénéficiaires (y compris HMM), les montants affichés sont généralement déjà en TTC.
   Extrayez ces deux totaux calculés en TTC comme DEUX éléments séparés dans votre tableau JSON, l'un pour "magasinage" et l'autre pour "surestarie").
2. Pour chaque facture (ou ligne de frais séparée), extrayez :
   - Le montant TTC (numérique).
   - Le bénéficiaire ou fournisseur.
   - Le numéro de la facture (UNIQUEMENT le numéro exact, sans le préfixe F/ ou Facture. Cherchez les numéros isolés en haut comme TI-...). S'il n'y en a pas, mettez une chaine vide "". (Note importante: pour le bénéficiaire CMA, la facture commence souvent par MAMI).
   - Le BL (Bill of Lading). Cherchez EXACTEMENT les mentions "BL", "B/L", "B/L No" ou "Connaissement". NE PRENEZ JAMAIS la référence de "Voyage" ou de "Booking". S'il n'y a pas de mention claire de BL ou de Connaissement, mettez une chaine vide "".
   - Le "type" de frais. 

Règles strictes pour le "type" de frais :
- Si la facture indique (Magasinage, Magasinage Eurogate, Terminal storage) -> VOUS DEVEZ ABSOLUMENT choisir "magasinage".
- Si la facture indique (Surestarie, Free det, detention, demurage fee, demurage...) -> choisissez "surestarie".
- Si la facture indique (THC, Droit de port, Frais d'agence, Frais de port, agency fee, frais de manutention...) -> choisissez "thc".
- PRIORITÉ: Si le mot "MAGASINAGE" apparait, c'est obligatoirement "magasinage".
- NOTE SPÉCIALE HAPAG-LLOYD : Si le bénéficiaire est Hapag-Lloyd (ou Hapag) et que la facture contient une ligne "INSPECTION FEE", vous devez prendre le MONTANT TOTAL de la facture (ex: TOTAL H.T. ou Total Général) et retourner UN SEUL élément JSON avec ce montant total et le type "inspection".

- Voici la liste des bénéficiaires de type IMPORTATION : [IMPORT_LIST]. Si le bénéficiaire correspond à l'un de ces noms (ou s'il s'agit d'un acteur maritime/portuaire/douanier), vous NE DEVEZ JAMAIS choisir "divers". Vous devez OBLIGATOIREMENT choisir l'un de ces types : "magasinage", "surestarie", "thc", "inspection", "change", ou "fret".
- Voici la liste des bénéficiaires de type DIVERS : [DIVERS_LIST]. Si le bénéficiaire correspond à l'un de ces noms, vous DEVEZ OBLIGATOIREMENT choisir "divers".[FEEDBACK]

Règles de formatage :
- Retournez UNIQUEMENT un objet JSON valide, sans formatage markdown, sans explications.
- Le JSON doit suivre cette structure exacte :
{
  "chq_number": "1234567",
  "chq_ste": "SOUFIANE NEGOCE",
  "chq_amount": 10500.50,
  "chq_date": "2026-08-15",
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
        
        stes = request.env['finance2.ste'].sudo().search([])
        stes_names = ", ".join([f"{s.name} ({s.raison_social or ''})" for s in stes])
        
        prompt_text = prompt_text.replace("[IMPORT_LIST]", import_list_str)
        prompt_text = prompt_text.replace("[DIVERS_LIST]", divers_list_str)
        prompt_text = prompt_text.replace("[FEEDBACK]", feedback_instruction)
        prompt_text = prompt_text.replace("[STES_LIST]", stes_names)
        
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
