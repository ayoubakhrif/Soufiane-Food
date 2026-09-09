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
        bl_number = str(ai_result.get('bl_number', '')).strip().upper()
        bl_number_filename = str(ai_result.get('bl_number_filename', '')).strip().upper()
        bad_date_str = ai_result.get('bad_date', '')

        if not bl_number and not bl_number_filename:
            return {'status': 'success', 'response': "❌ L'IA n'a pas pu identifier le numéro de BL dans le PDF ni dans le nom du fichier."}

        # 5. Find Dossier and Entry
        # Try finding by document BL first
        dossier = request.env['logistique.dossier'].sudo().search([('name', '=ilike', bl_number)], limit=1) if bl_number else False
        
        # If not found, try finding by filename BL
        if not dossier and bl_number_filename:
            dossier_fallback = request.env['logistique.dossier'].sudo().search([('name', '=ilike', bl_number_filename)], limit=1)
            if dossier_fallback:
                dossier = dossier_fallback
                bl_number = bl_number_filename
        
        if not dossier:
             return {'status': 'not_found', 'message': f"❌ Aucun dossier trouvé pour le BL: {bl_number or bl_number_filename}."}

        entry = request.env['logistique.entry'].sudo().search([('dossier_id', '=', dossier.id)], limit=1)
        
        if not entry:
            return {'status': 'not_found', 'message': f"❌ Aucune entrée logistique trouvée pour le dossier BL: {dossier.name}."}

        messages = []
        
        dossier_msg = f"🔹 *Dossier (BL)* : {dossier.name}"
        bad_msg = ""
        chq_msg = ""
        factures_msgs = []

        # 6. Update BAD Date
        if bad_date_str and bad_date_str.lower() != 'none':
            try:
                # the AI is instructed to return YYYY-MM-DD
                bad_date_obj = datetime.strptime(bad_date_str, '%Y-%m-%d').date()
                entry.write({'bad_date': bad_date_obj})
                bad_msg = f"📅 *Date de BAD* : {bad_date_obj.strftime('%d/%m/%Y')}"
            except Exception as e:
                bad_msg = f"⚠️ *Date de BAD* : Impossible de parser ({bad_date_str})"

        if not chq_number:
            chq_msg = "⚠️ Aucun numéro de chèque identifié."
        elif not factures:
            chq_msg = "⚠️ Aucune facture identifiée dans le document."
        else:
            chq_msg = f"🧾 *Chèque N°* : {chq_number}"
            
            # Check if any divisions for this cheque already exist in the dossier (optional protection)
            existing_cheques = request.env['logistique.dossier.cheque'].sudo().search([
                ('dossier_id', '=', dossier.id),
                ('cheque_serie', '=', chq_number)
            ])
            
            if existing_cheques:
                factures_msgs.append("ℹ️ _(Des lignes existent déjà pour ce chèque dans ce dossier, de nouvelles ont été ajoutées)_")

            for idx, inv_data in enumerate(factures):
                inv_amount = float(inv_data.get('montant', 0))
                inv_type = inv_data.get('type', 'autres').lower()
                inv_benif_name = inv_data.get('beneficiaire', '')

                # Match Beneficiary in logistique.shipping
                benif_record = False
                if inv_benif_name:
                    benif_record = request.env['logistique.shipping'].sudo().search([('name', 'ilike', inv_benif_name)], limit=1)

                if inv_type not in ['thc', 'magasinage', 'fret', 'surestarie', 'assurance', 'autres']:
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
                    request.env['logistique.dossier.cheque'].sudo().with_context(from_bot=True).create(vals)
                    benif_display = benif_record.name if benif_record else inv_benif_name
                    factures_msgs.append(f"  • *{inv_amount:,.2f} DH* ({vals['type'].capitalize()}) - {benif_display}")
                except Exception as e:
                    pass  # Ignorer l'affichage de l'erreur sur WhatsApp selon la demande

        # 7. Add PDF to documents as Facture Compagnie
        doc_msg = ""
        if pdf_base64 and 'logistique.entry.document' in request.env:
            try:
                DocModel = request.env['logistique.entry.document'].sudo()
                doc_filename = file_name if file_name and file_name != 'document.pdf' else f"Facture_Compagnie_{dossier.name}_{chq_number or ''}.pdf"
                
                existing_doc = DocModel.search([
                    ('entry_id', '=', entry.id),
                    ('document_type', '=', 'company_invoice'),
                    ('file_name', '=', doc_filename)
                ], limit=1)
                
                if not existing_doc:
                    DocModel.create({
                        'entry_id': entry.id,
                        'document_type': 'company_invoice',
                        'file': pdf_base64,
                        'file_name': doc_filename
                    })
                    doc_msg = "📎 *Document* : Ajouté aux Factures companies"
                else:
                    doc_msg = "📎 *Document* : Factures companies (déjà présent)"
            except Exception as e:
                _logger.error(f"Erreur enregistrement document facture compagnie pour {dossier.name}: {str(e)}")

        final_response = "✅ *Données saisies avec succès dans Gestia :*\n━━━━━━━━━━━━━━━━━━\n"
        final_response += f"{dossier_msg}\n"
        if bad_msg:
            final_response += f"{bad_msg}\n"
        if chq_msg:
            final_response += f"{chq_msg}\n"
        if doc_msg:
            final_response += f"{doc_msg}\n"
        
        if factures_msgs:
            final_response += "\n📊 *Factures réparties :*\n"
            final_response += "\n".join(factures_msgs).replace(',', ' ')
            
        return {
            'status': 'success',
            'response': final_response
        }

    def _extract_data_from_pdf(self, pdf_b64, file_name, api_key):
        """Use OpenAI to extract cheque, invoices and BAD data from PDF."""
        # Get shipping lists to guide the AI for beneficiaries
        shippings = request.env['logistique.shipping'].sudo().search([]).mapped('name')
        shipping_list_str = ", ".join(shippings) if shippings else "Aucun"

        prompt_text = f"""Vous êtes un assistant logistique. Vous recevez un document (PDF) qui contient généralement un chèque, une ou plusieurs factures, et parfois un Bon à Délivrer (BAD).
Le nom du fichier est : {file_name}

Votre but est d'analyser le document et d'extraire les informations nécessaires pour l'ERP Odoo.

1. Trouvez le numéro de chèque (généralement 7 chiffres consécutifs). S'il n'y en a pas, mettez une chaîne vide "".
2. Trouvez le numéro de BL (Bill of Lading, Connaissement maritime, ex: YMJAM450339005) à l'intérieur du document PDF. Cherchez "BL", "B/L", ou une longue référence alphanumérique liée au navire/conteneur. Mettez le résultat dans "bl_number".
3. Extrayez également le numéro de BL indiqué dans le nom du fichier (qui est : {file_name}) et mettez-le dans "bl_number_filename". Ne le cherchez pas dans le document, lisez uniquement le nom du fichier. Par exemple, si le nom est 'bl CFA0903943.pdf', renvoyez 'CFA0903943'. S'il n'y a pas de BL dans le nom, mettez "".
4. Trouvez la date du BAD (Bon à Délivrer). Si vous trouvez une date associée au BAD, retournez-la au format YYYY-MM-DD. Sinon, "".
5. Pour chaque facture (ou ligne de frais séparée) associée, extrayez :
   - Le montant TTC (numérique).
   - Le bénéficiaire ou fournisseur. Voici la liste des compagnies maritimes connues : [SHIPPING_LIST]. Essayez de mapper le bénéficiaire à l'un de ces noms.
   - Le "type" de frais.

Règles strictes pour le "type" de frais :
- Si la facture indique (Magasinage, Magasinage Eurogate, Terminal storage, taxe regional) -> VOUS DEVEZ ABSOLUMENT choisir "magasinage".
- Si la facture indique (Surestarie, Free det, detention, demurage fee, demurage...) -> choisissez "surestarie".
- Si la facture indique (THC, Droit de port, Frais d'agence, Frais de port, agency fee, frais de manutention...) -> choisissez "thc".
- Si la facture indique (Fret, Freight, Sea Freight...) -> choisissez "fret".
- Si la facture indique (Assurance, Premium, Prime...) -> choisissez "assurance".
- PRIORITÉ: Si le mot "MAGASINAGE" apparait, c'est obligatoirement "magasinage".
- Si aucun de ces types ne correspond, mettez "autres".

   (NOTE SPÉCIALE TRÈS IMPORTANTE POUR FACTURES CMA CGM ET HMM) :
   Sur les factures CMA CGM (qui comportent souvent plusieurs conteneurs et s'étendent sur plusieurs pages) :
   1. COLONNE À LIRE POUR CHAQUE CONTENEUR :
      - Lisez UNIQUEMENT la dernière colonne intitulée "Montant Total" (en dirhams / MAD).
      - NE CONFONDEZ JAMAIS avec les colonnes "Nombre de jours facturables", "Jours", "Free Days" (ex: '2', '21', '1', etc.) ou "Taux" qui ne sont PAS des montants !
      - Parcourez TOUTES LES PAGES pour comptabiliser TOUS LES CONTENEURS :
        * Sous "(L) Terminal full storage at destination", additionnez le "Montant Total" de CHAQUE conteneur sur toutes les pages (ex: 5 conteneurs à 120 MAD = 600 MAD).
        * Sous "(C) Detention & Demurrage Import Charge", additionnez le "Montant Total" de CHAQUE conteneur sur toutes les pages (ex: 5 conteneurs à 460 MAD = 2300 MAD).
   
   2. TAXE RÉGIONALE :
      - Le montant sous "Charges Diverses" -> "(L) Taxe Regionale" (ex: 24.00 MAD) DOIT TOUJOURS ÊTRE AJOUTÉ au montant de "magasinage".
      (Note : La colonne "Base taxabl" de la Taxe Régionale indique d'ailleurs exactement le total HT du stockage !).

   3. GESTION DE LA TVA (CAS SANS TVA vs CAS AVEC TVA) :
      - CAS SANS TVA (Mention Taxe 'ME' / Régime suspensif / Exonéré) :
        Il n'y a PAS de tableau de TVA en bas. Les montants des conteneurs sont déjà définitifs.
        Total Magasinage = (Somme stockage L) + (Taxe Régionale L).
        Total Surestarie = (Somme surestarie C).
      - CAS AVEC TVA (Tableau de TVA au bas de la facture) :
        Ajoutez la TVA commençant par "L TVA" au magasinage.
        Ajoutez la TVA commençant par "C TVA" à la surestarie.

   4. CONTRÔLE DE COHÉRENCE OBLIGATOIRE :
      - La facture indique TOUJOURS son montant total global au bas de la dernière page (ex: "Montant Total: 2 924.00 MAD" ou "Total T.T.C").
      - Vérifiez IMPÉRATIVEMENT que :
        Total Magasinage + Total Surestarie == Montant Total de la facture !
      - Si votre total calculé ne correspond pas au "Montant Total" de la facture, votre calcul est FAUX : vous avez manqué des conteneurs ou confondu avec le nombre de jours. Corrigez-le avant de renvoyer le JSON.
   
   Extrayez ces deux montants exacts dans la liste "factures", l'un avec le type "magasinage" et l'autre avec le type "surestarie".
Règles de formatage :
- Retournez UNIQUEMENT un objet JSON valide, sans formatage markdown, sans explications.
- Le JSON doit suivre cette structure exacte :
{{
  "chq_number": "1234567",
  "bl_number": "YMJAM450339005",
  "bl_number_filename": "CFA0903943",
  "bad_date": "2023-10-15",
  "factures": [
    {{
      "montant": 10500.50,
      "beneficiaire": "Tanger Med",
      "type": "magasinage",
      "numero_facture": "2023-001"
    }}
  ]
}}
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
