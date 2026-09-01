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

        if not bl_code or (isinstance(bl_code, str) and bl_code.upper() == 'IGNORE'):
            _logger.info(f"Ignoring message in Logistics Payment Bot: {message_text}")
            return {'status': 'ignored'}

        if isinstance(bl_code, str) and bl_code.upper() == 'NONE':
            return {'status': 'not_found', 'message': "❌ Aucune référence (BL, Facture, Lot, Conteneur) n'a pu être identifiée dans votre message."}

        # 5. Search for the dossier / BL
        dossier = self._find_dossier_by_ref(bl_code)
        
        ref_str = bl_code.get('ref', str(bl_code)) if isinstance(bl_code, dict) else str(bl_code)
        if not dossier:
            return {'status': 'not_found', 'message': f"❌ Aucun dossier trouvé pour la référence '{ref_str}'."}

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
        
        invoice_val = entry.invoice_number if entry and entry.invoice_number else 'N/A'
        week_val = entry.week if entry and entry.week else 'N/A'
        saisi_par_val = entry.saisi_par if entry and entry.saisi_par else 'N/A'

        response += f"🏢 *Société* : {ste_name}\n"
        response += f"👤 *Fournisseur* : {supplier_name}\n"
        response += f"📦 *Article* : {article_name}\n"
        response += f"🌐 *Incoterm* : {incoterm_val}\n"

        # Additional Fields from Image Section 1 & 2
        shipping_name = 'N/A'
        if entry and entry.shipping_id:
            shipping_name = entry.shipping_id.name or 'N/A'
        
        container_count = dossier.container_count or (entry and entry.container_count) or 0
        container_names = dossier.container_names or (entry and entry.container_names) or 'N/A'
        
        size_val = 'N/A'
        if entry and hasattr(entry, 'container_size') and entry.container_size:
            size_val = dict(entry._fields['container_size'].selection or {}).get(entry.container_size, entry.container_size)
            if size_val == '20':
                size_val = "20'"
            elif size_val == '40':
                size_val = "40'"
        
        port_status_val = 'N/A'
        if entry and entry.port_status:
            port_status_val = dict(entry._fields['port_status'].selection or {}).get(entry.port_status, entry.port_status)
        
        franchise_val = 'N/A'
        if entry and hasattr(entry, 'free_time') and entry.free_time:
            franchise_val = f"{entry.free_time}j"
        elif entry and hasattr(entry, 'free_time_negotiated') and entry.free_time_negotiated:
            franchise_val = f"{entry.free_time_negotiated}j"
            
        response += f"🚢 *Compagnie* : {shipping_name}\n"
        response += f"🔢 *Nombre Conteneurs* : {container_count}\n"
        response += f"🔠 *N° Conteneurs* : {container_names}\n"
        response += f"📐 *Taille* : {size_val}\n"
        response += f"⚓ *Port Status* : {port_status_val}\n"
        response += f"⏳ *Franchise confirmée* : {franchise_val}\n"
        response += f"🧾 *Facture N°* : {invoice_val}\n"
        response += f"📅 *Semaine* : {week_val}\n"
        response += f"✍️ *Saisi par* : {saisi_par_val}\n\n"
        
        # Additional Dates from Image Section 3
        bad_date_str = entry.bad_date.strftime('%d/%m/%Y') if entry and entry.bad_date else 'N/A'
        exit_date_str = entry.exit_date.strftime('%d/%m/%Y') if entry and entry.exit_date else 'N/A'
        entry_date_str = entry.entry_date.strftime('%d/%m/%Y') if entry and entry.entry_date else 'N/A'
        
        dhl_date_val = dossier.eta_dhl or (entry and entry.eta_dhl) or False
        dhl_date_str = dhl_date_val.strftime('%d/%m/%Y') if dhl_date_val else 'N/A'
        
        response += f"📅 *Dates* :\n"
        response += f"• 📅 *ETA* : {eta_str}\n"
        response += f"• 📦 *DHL* : {dhl_date_str}\n"
        response += f"• 📄 *BAD* : {bad_date_str}\n"
        response += f"• 🚪 *D. Sortie* : {exit_date_str}\n"
        response += f"• 📥 *D. Entré* : {entry_date_str}\n\n"
        
        response += f"📊 *Charges engagées* :\n"
        response += f"• 🚢 *Fret* : {dossier.fret_amount:,.2f} DH\n"
        response += f"• ⚓ *THC* : {dossier.thc_amount:,.2f} DH\n"
        response += f"•     Magasinage : {dossier.magasinage_amount:,.2f} DH\n"
        response += f"• ⏳ *Surestarie* : {dossier.surestarie_amount:,.2f} DH\n"
        response += f"• 🛡️ *Assurance* : {dossier.assurance_amount:,.2f} DH\n\n"

        # Apply Moroccan Dirham spacing format
        response = response.replace(',', ' ')

        # A. Details Chèques
        if dossier.cheque_ids:
            response += f"🧾 *Détails des Chèques* :\n"
            
            # Grouping/sorting order: fret, thc, magasinage, surestarie, assurance, autres
            type_order = ['fret', 'thc', 'magasinage', 'surestarie', 'assurance', 'autres']
            cheques_by_type = {t: [] for t in type_order}
            
            for c in dossier.cheque_ids:
                t = c.type if c.type in type_order else 'autres'
                cheques_by_type[t].append(c)
                
            type_headers = {
                'fret': '🚢 *Fret*',
                'thc': '⚓ *THC*',
                'magasinage': '📦 *Magasinage*',
                'surestarie': '⏳ *Surestarie*',
                'assurance': '🛡️ *Assurance*',
                'autres': '➕ *Autres factures*'
            }
            
            for t in type_order:
                cheques = cheques_by_type[t]
                if cheques:
                    header = type_headers.get(t, t.capitalize())
                    response += f"  • {header} :\n"
                    for c in cheques:
                        status = "⏳ En cours (Non rapproché)"
                        fin_chq = request.env['finance.cheque.physical'].sudo().search([('name', '=', c.cheque_serie)], limit=1)
                        if fin_chq:
                            is_encaissé = fin_chq.encours == 'encaisse' or any(d.date_encaissement for d in fin_chq.datacheque_ids)
                            if is_encaissé:
                                enc_date = fin_chq.date_encaissement or next((d.date_encaissement for d in fin_chq.datacheque_ids if d.date_encaissement), False)
                                status = f"✅ Encaissé le {enc_date.strftime('%d/%m/%Y')}" if enc_date else "✅ Encaissé"
                            else:
                                status = "⏳ Non encaissé"
                        
                        benef = c.beneficiary_id.name or "N/A"
                        chq_line = f"    - Chq *#{c.cheque_serie}* : *{c.amount:,.2f} DH* | {benef} | {status}\n"
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
            response += "\n"

        # F. Charges Douane
        if entry:
            transit = getattr(entry, 'transit_fees', 0.0) or 0.0
            douane = getattr(entry, 'customs_duty', 0.0) or 0.0
            temsa = getattr(entry, 'temsa', 0.0) or 0.0
            
            if transit > 0 or douane > 0 or temsa > 0:
                response += f"🛂 *Charges Douane* :\n"
                if transit > 0:
                    response += f"  • Frais de transit : *{transit:,.2f} DH*\n".replace(',', ' ')
                if douane > 0:
                    response += f"  • Droit de douane : *{douane:,.2f} DH*\n".replace(',', ' ')
                if temsa > 0:
                    response += f"  • TEMSA : *{temsa:,.2f} DH*\n".replace(',', ' ')
                response += "\n"

        # G. Réclamations (Charges à récupérer)
        if entry_ids:
            claims_models = [
                ('claims.quantity', 'Quantité'),
                ('claims.quality', 'Qualité'),
                ('claims.dhl.delay', 'DHL Delay'),
                ('claims.franchise.difference', 'Franchise'),
                ('claims.divers', 'Divers')
            ]
            claims_found = []
            responsibles = set()
            total_amount_due = 0.0
            states_info = []
            
            for model_name, type_label in claims_models:
                if model_name in request.env:
                    records = request.env[model_name].sudo().search([('bl_id', 'in', entry_ids)])
                    for r in records:
                        claims_found.append((type_label, r))
                        if r.responsible_id:
                            responsibles.add(r.responsible_id.name)
                        total_amount_due += r.amount_due or 0.0
                        
                        # Gather status / dates
                        state_label = dict(r._fields['state'].selection or {}).get(r.state, r.state).capitalize()
                        date_str = ""
                        if r.state == 'initial' and hasattr(r, 'claim_date') and r.claim_date:
                            date_str = r.claim_date.strftime('%d/%m/%y')
                        elif r.state == 'received' and hasattr(r, 'date_received') and r.date_received:
                            date_str = r.date_received.strftime('%d/%m/%y')
                        elif r.state == 'waiting' and hasattr(r, 'date_waiting') and r.date_waiting:
                            date_str = r.date_waiting.strftime('%d/%m/%y')
                        elif r.state == 'refused' and hasattr(r, 'date_refused') and r.date_refused:
                            date_str = r.date_refused.strftime('%d/%m/%y')
                        elif r.state == 'resolved' and hasattr(r, 'date_resolved') and r.date_resolved:
                            date_str = r.date_resolved.strftime('%d/%m/%y')
                        elif r.state == 'closed' and hasattr(r, 'date_closed') and r.date_closed:
                            date_str = r.date_closed.strftime('%d/%m/%y')
                        
                        if date_str:
                            states_info.append(f"{state_label} ({date_str})")
                        else:
                            states_info.append(f"{state_label}")

            if claims_found:
                response += f"⚠️ *Réclamations (charges à récupérer)* :\n"
                resp_str = ", ".join(responsibles) if responsibles else "Non assigné"
                response += f"• 👤 *Responsable* : {resp_str}\n"
                
                for type_label, r in claims_found:
                    if type_label == 'DHL Delay':
                        response += f"• ✉️ *DHL* : {r.dhl_delay}j retard\n"
                    elif type_label == 'Franchise':
                        response += f"• ⏳ *Franchise* : Franchise trouvée : {r.franchise_found:.0f} j / diff : {r.franchise_difference:.0f} j\n"
                    elif type_label == 'Quantité':
                        response += f"• 📦 *Quantité* : Manquante : {r.missing_quantity:.2f}\n"
                    elif type_label == 'Qualité':
                        response += f"• 🔬 *Qualité* : Dossier Qualité disponible\n"
                    elif type_label == 'Divers':
                        response += f"• ➕ *Divers* : Réclamation divers active\n"
                
                # Fetch Currency Exchange Rate
                usd_currency = request.env['res.currency'].sudo().search([('name', '=', 'USD')], limit=1)
                exchange_rate = 9.15
                if usd_currency and usd_currency.rate:
                    if usd_currency.rate < 1.0:
                        exchange_rate = 1.0 / usd_currency.rate
                
                total_amount_due_mad = total_amount_due * exchange_rate
                
                response += f"• 💰 *Montant à récupérer* : {total_amount_due:,.2f} USD / {total_amount_due_mad:,.2f} DH\n"
                if states_info:
                    response += f"• 🔄 *Status* : { ' / '.join(states_info) }\n"
                response += "\n"

        # Apply final Moroccan spacing (replace commas with spaces)
        response = response.replace(',', ' ')

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
                "Tu es un assistant logistique et financier. Ta tâche est d'identifier la référence mentionnée dans le message WhatsApp de l'utilisateur.\n"
                "La référence peut être un BL (Bill of Lading), un numéro de Facture, un Lot, ou un Numéro de Conteneur.\n"
                "Message de l'utilisateur : " + text + "\n\n"
                "Règles :\n"
                "1. Identifie la référence et son type (BL, FACTURE, LOT, ou CONTENEUR).\n"
                "2. Si le message ne contient que des salutations, emojis ou caractères non pertinents sans rapport, réponds uniquement 'IGNORE'.\n"
                "3. S'il n'y a pas de référence identifiable, réponds uniquement 'NONE'.\n"
                "4. Sinon, retourne UNIQUEMENT un objet JSON valide avec les clés 'type' (BL, FACTURE, LOT, CONTENEUR) et 'ref' (la référence brute).\n"
                "Exemple : {\"type\": \"BL\", \"ref\": \"26018888\"}"
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
                if extracted.upper() in ['NONE', 'IGNORE']:
                    return extracted
                try:
                    import json
                    if extracted.startswith('```json'):
                        extracted = extracted.replace('```json', '').replace('```', '').strip()
                    elif extracted.startswith('```'):
                        extracted = extracted.replace('```', '').strip()
                    data = json.loads(extracted)
                    return data
                except Exception as parse_e:
                    _logger.error(f"OpenAI JSON Parse Error: {str(parse_e)} - Content: {extracted}")
                    return extracted
            except Exception as e:
                _logger.error(f"OpenAI BL Extraction Error: {str(e)}")
                
        # 3. Fallback: Cleanup common prefix and check if it's a code
        cleaned = re.sub(r'(?i)^(bl|dossier|ref|reference)\s*[:\-\s]+', '', text_clean)
        if re.match(r'^[A-Z0-9.\-_/]+$', cleaned.upper()):
            return cleaned
            
        return text_clean

    def _find_dossier_by_ref(self, ref_data):
        """Search all dossiers and filter by normalized name or specific fields."""
        if not ref_data:
            return None
            
        ref = ref_data
        if isinstance(ref_data, dict):
            ref = ref_data.get('ref', '')
            
        if not ref:
            return None
            
        norm_ref = self.normalize_ref(ref)
        
        # 1. Exact match BL
        exact_dossier = request.env['logistique.dossier'].sudo().search([('name', '=', ref)], limit=1)
        if exact_dossier:
            return exact_dossier
            
        # 2. Search BL Normalized
        norm_dossiers = request.env['logistique.dossier'].sudo().search([])
        for d in norm_dossiers:
            if self.normalize_ref(d.name) == norm_ref:
                return d
                
        # 3. Search Invoice (Case-insensitive)
        entry = request.env['logistique.entry'].sudo().search([('invoice_number', 'ilike', ref)], limit=1)
        if entry and entry.dossier_id:
            return entry.dossier_id
            
        # 4. Search Lot (Case-insensitive)
        entry = request.env['logistique.entry'].sudo().search([('lot', 'ilike', ref)], limit=1)
        if entry and entry.dossier_id:
            return entry.dossier_id
            
        # 5. Search Container (Case-insensitive)
        container = request.env['logistique.container'].sudo().search([('name', 'ilike', ref)], limit=1)
        if container and container.entry_id and container.entry_id.dossier_id:
            return container.entry_id.dossier_id
            
        return None
