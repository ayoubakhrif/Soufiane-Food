import base64
import json
import logging
import requests
import re
from datetime import date
from odoo import http, SUPERUSER_ID, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppLogisticsPaymentController(http.Controller):

    def normalize_ref(self, val):
        """Removes ALL non-alphanumeric characters and converts to uppercase."""
        if not val:
            return ""
        return re.sub(r'[^A-Z0-9]', '', str(val).upper())

    @http.route('/api/whatsapp/logistics_payment', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_logistics_payment_report(self, **kwargs):
        # Force database session
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        # 1. API Key Verification
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'default-secret-key')
        
        if not api_key or api_key != expected_api_key:
            _logger.warning("Unauthorized access attempt to WhatsApp Logistics Payment API")
            return {'status': 'error', 'message': 'Unauthorized'}

        # 2. Extract Data
        data = kwargs
        message_text = data.get('message', '').strip()
        group_id = data.get('group_id', '')

        if not message_text:
            return {'status': 'error', 'message': 'Empty message'}

        # 3. Target Group Verification
        LOGISTICS_PAYMENT_GROUP_ID = '120363407897068761@g.us'
        if group_id != LOGISTICS_PAYMENT_GROUP_ID:
            _logger.info(f"Ignoring request from group {group_id} in Logistics Payment Agent")
            return {'status': 'ignored', 'message': 'This agent only handles the Logistics Payment Group.'}

        # 4. Extract BL Code using OpenAI or fallback
        openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        bl_code = self._extract_bl_code(message_text, openai_key)

        if not bl_code or bl_code.upper() == 'IGNORE':
            _logger.info(f"Ignoring message in Logistics Payment Bot: {message_text}")
            return {'status': 'ignored'}

        if bl_code.upper() == 'NONE':
            return {'status': 'not_found', 'message': "❌ Aucun numéro de BL n'a pu être identifié dans votre message. Veuillez envoyer un numéro de BL valide."}

        # 5. Search for the dossier / BL
        dossier = self._find_dossier_by_ref(bl_code)
        if not dossier:
            return {'status': 'not_found', 'message': f"❌ Aucun dossier trouvé pour le BL '{bl_code}'."}

        # 6. Format Response
        response = f"📋 *Paiements du BL : {dossier.name}*\n"
        response += f"━━━━━━━━━━━━━━━━━━\n\n"
        
        # Fallback dynamically to the first linked entry if common fields are empty on the dossier record
        entry = dossier.entry_ids[0] if dossier.entry_ids else None
        
        ste_name = dossier.ste_id.name or (entry and entry.ste_id.name) or 'N/A'
        supplier_name = dossier.supplier_id.name or (entry and entry.supplier_id.name) or 'N/A'
        
        eta_val = dossier.eta or (entry and entry.eta) or False
        eta_str = eta_val.strftime('%d/%m/%Y') if eta_val else 'N/A'
        
        # Article (achat_article_id from achat module or fallback to article_id) and Incoterm (extracted from entry)
        article_name = 'N/A'
        if entry:
            if hasattr(entry, 'achat_article_id') and entry.achat_article_id:
                article_name = entry.achat_article_id.name or 'N/A'
            elif entry.article_id:
                article_name = entry.article_id.name or 'N/A'
        
        incoterm_val = 'N/A'
        if entry and entry.incoterm:
            incoterm_val = dict(entry._fields['incoterm'].selection or {}).get(entry.incoterm, entry.incoterm).upper()
        
        response += f"🏢 *Société* : {ste_name}\n"
        response += f"👤 *Fournisseur* : {supplier_name}\n"
        response += f"📦 *Article* : {article_name}\n"
        response += f"🌐 *Incoterm* : {incoterm_val}\n"
        response += f"📅 *ETA* : {eta_str}\n\n"
        
        response += f"📊 *Synthèse des Charges* :\n"
        response += f"• 🚢 *Fret* : {dossier.fret_amount:,.2f} DH\n"
        response += f"• ⚓ *THC* : {dossier.thc_amount:,.2f} DH\n"
        response += f"•     Magasinage : {dossier.magasinage_amount:,.2f} DH\n"
        response += f"• ⏳ *Surestarie* : {dossier.surestarie_amount:,.2f} DH\n\n"

        # Apply Moroccan Dirham spacing format
        response = response.replace(',', ' ')

        # A. Details Chèques
        if dossier.cheque_ids:
            response += f"🧾 *Détails des Chèques* :\n"
            for c in dossier.cheque_ids:
                status = "⏳ En cours (Non rapproché)"
                fin_chq = request.env['finance.cheque.physical'].sudo().search([('name', '=', c.cheque_serie)], limit=1)
                if fin_chq:
                    is_encaissé = fin_chq.encours == 'encaisse' or any(d.date_encaissement for d in fin_chq.datacheque_ids)
                    status = "✅ Encaissé" if is_encaissé else "⏳ En cours"
                
                type_label = dict(c._fields['type'].selection or {}).get(c.type, c.type or "N/A").upper()
                benef = c.beneficiary_id.name or "N/A"
                chq_line = f"• Chq *#{c.cheque_serie}* ({type_label}) : *{c.amount:,.2f} DH* | {benef} | {status}\n"
                response += chq_line.replace(',', ' ')
            response += "\n"

        # B. Details Virements
        if dossier.transfer_ids:
            response += f"💸 *Détails des Virements* :\n"
            for t in dossier.transfer_ids:
                type_label = dict(t._fields['type'].selection or {}).get(t.type, t.type or "N/A").upper()
                benef = t.beneficiary_id.name or "N/A"
                date_str = t.date.strftime('%d/%m/%Y') if t.date else "N/A"
                transfer_line = f"• Virement du {date_str} ({type_label}) : *{t.amount:,.2f} DH* | {benef}\n"
                response += transfer_line.replace(',', ' ')
            response += "\n"

        # C. Details Déductions
        if dossier.deduction_ids:
            response += f"➖ *Détails des Déductions* :\n"
            for d in dossier.deduction_ids:
                type_label = dict(d._fields['type'].selection or {}).get(d.type, d.type or "N/A").upper()
                benef = d.beneficiary_id.name or "N/A"
                date_str = d.date.strftime('%d/%m/%Y') if d.date else "N/A"
                deduction_line = f"• Déduction du {date_str} ({type_label}) : *{d.amount:,.2f} DH* | {benef}\n"
                response += deduction_line.replace(',', ' ')
            response += "\n"

        # D. Details Sutra Logistique
        if dossier.sutra_ids:
            response += f"📑 *Lignes Sutra (Logistique)* :\n"
            for s in dossier.sutra_ids:
                type_label = dict(s._fields['type'].selection or {}).get(s.type, s.type or "N/A").upper()
                benef = s.beneficiary_id.name or "N/A"
                date_str = s.date.strftime('%d/%m/%Y') if s.date else "N/A"
                s_line = f"• Sutra du {date_str} ({type_label}) : *{s.amount:,.2f} DH* | Facture: {s.invoice or 'N/A'} | {benef}\n"
                response += s_line.replace(',', ' ')
            response += "\n"

        # E. Details Règlements Finance (Sutra / Marglory)
        entry_ids = dossier.entry_ids.ids
        sutra_recs = request.env['finance.sutra'].sudo().search([('douane_id', 'in', entry_ids)]) if entry_ids else []
        marglory_recs = request.env['finance.marglory'].sudo().search([('douane_id', 'in', entry_ids)]) if entry_ids else []

        if sutra_recs or marglory_recs:
            response += f"💼 *Règlements de la Finance* :\n"
            if sutra_recs:
                response += f"  *Factures Sutra* :\n"
                for s in sutra_recs:
                    status = "✅ Encaissé" if s.is_encaisse else "⏳ En cours"
                    chq_str = f"Chq #{s.cheque_number}" if s.cheque_number else "Pas de chèque"
                    s_fin_line = f"  • Facture *{s.facture_sutra or 'N/A'}* : *{s.total:,.2f} DH* | {chq_str} | {status}\n"
                    response += s_fin_line.replace(',', ' ')
            if marglory_recs:
                response += f"  *Factures Marglory* :\n"
                for m in marglory_recs:
                    status = "✅ Encaissé" if m.is_encaisse else "⏳ En cours"
                    chq_str = f"Chq #{m.cheque_number}" if m.cheque_number else "Pas de chèque"
                    type_str = m.type or "N/A"
                    m_fin_line = f"  • Facture *{m.facture_marglory or 'N/A'}* ({type_str}) : *{m.amount:,.2f} DH* | {chq_str} | {status}\n"
                    response += m_fin_line.replace(',', ' ')

        return {'status': 'response', 'response': response}

    def _extract_bl_code(self, text, api_key=None):
        """Extract the BL reference from the message."""
        if not text:
            return None
        
        text_clean = text.strip()
        
        # 1. Direct search pattern "bl medut12345" or similar
        bl_match = re.search(r"(?i)^bl\s*[:(\s]*([A-Z0-9.\-_/]+)[)\s]*$", text_clean)
        if bl_match:
            return bl_match.group(1)
            
        # 2. OpenAI advanced extraction
        if api_key:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            prompt = (
                "Tu es un assistant logistique et financier. Ta tâche est d'identifier la référence du BL (Bill of Lading / Bon de Livraison) mentionnée dans le message WhatsApp de l'utilisateur.\n"
                "La référence d'un BL est généralement une chaîne alphanumérique (par exemple : MEDUT7846505, HLCUBSC2511BEGMO, MSCU1234567, etc.) ou parfois plus courte.\n"
                "Message de l'utilisateur : " + text + "\n\n"
                "Règles :\n"
                "1. Extrais uniquement la référence brute du BL.\n"
                "2. S'il n'y a pas de référence de BL identifiable, réponds uniquement 'NONE'.\n"
                "3. Si le message ne contient que des salutations, emojis ou caractères non pertinents, réponds uniquement 'IGNORE'.\n"
                "Retourne UNIQUEMENT le résultat (sans explications, sans markdown)."
            )
            data = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0
            }
            try:
                response = requests.post(url, headers=headers, json=data, timeout=10)
                result = response.json()
                extracted = result['choices'][0]['message']['content'].strip()
                if extracted:
                    return extracted
            except Exception as e:
                _logger.error(f"OpenAI BL Extraction Error: {str(e)}")
                
        # 3. Fallback: Cleanup common prefix and check if it's a code
        cleaned = re.sub(r'(?i)^(bl|dossier|ref|reference)\s*[:\-\s]+', '', text_clean)
        if re.match(r'^[A-Z0-9.\-_/]+$', cleaned.upper()):
            return cleaned
            
        return text_clean

    def _find_dossier_by_ref(self, ref):
        """Search all dossiers and filter by normalized name."""
        if not ref:
            return None
        norm_ref = self.normalize_ref(ref)
        
        # Exact match check first
        exact_dossier = request.env['logistique.dossier'].sudo().search([('name', '=', ref)], limit=1)
        if exact_dossier:
            return exact_dossier

        # Fuzzy normalized search using wildcards
        flexible_search = '%' + '%'.join(list(norm_ref)) + '%'
        candidates = request.env['logistique.dossier'].sudo().search([('name', 'ilike', flexible_search)])
        for d in candidates:
            if self.normalize_ref(d.name) == norm_ref or norm_ref in self.normalize_ref(d.name):
                return d
        return None
