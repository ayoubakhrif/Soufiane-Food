import json
import logging
import re
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsappDocumentSearchApi(http.Controller):

    @http.route('/api/whatsapp/dossier_search', type='json', auth='none', methods=['POST'], csrf=False)
    def handle_dossier_search(self, **kw):
        try:
            # Check API Key
            api_key = request.httprequest.headers.get('X-Api-Key')
            valid_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'whatsapp_direct_quantity')
            if api_key != valid_api_key:
                return {'error': 'Invalid API Key', 'status': 401}

            query = kw.get('message', '').strip()
            if not query:
                return {
                    'status': 'ignored',
                    'message': 'Aucun critère de recherche fourni.'
                }

            # Handle Situation Report
            situation_match = re.match(r'^situation\s+(w\d{2})$', query, re.IGNORECASE)
            if situation_match:
                week = situation_match.group(1).upper()
                return self._generate_situation_report(week)

            # Handle Document Fetch
            if 'FETCH_DOC_SEARCH:' in query:
                parts = [p for p in query.split('|') if p.startswith('FETCH_DOC_SEARCH:')]
                if parts:
                    documents_to_send = []
                    names_to_send = []
                    
                    for part in parts:
                        subparts = part.split(':')
                        if len(subparts) == 3:
                            doc_model = subparts[1]
                            doc_id = int(subparts[2])
                            doc = request.env[doc_model].sudo().browse(doc_id)
                            if doc.exists() and doc.file:
                                doc_type_dict = dict(doc._fields['document_type'].selection)
                                doc_name = doc_type_dict.get(doc.document_type, str(doc.document_type))
                                file_name = doc.file_name or f"{doc_name}.pdf"
                                
                                base64_str = doc.file.decode('utf-8') if isinstance(doc.file, bytes) else doc.file
                                documents_to_send.append({
                                    'file_name': file_name,
                                    'base64': base64_str,
                                    'mimetype': 'application/pdf',
                                    'caption': f"Voici le document *{file_name}* demandé."
                                })
                                names_to_send.append(file_name)
                    
                    if documents_to_send:
                        # Ensure the response has 'files' mapped to our list
                        return {
                            'status': 'success',
                            'files': documents_to_send
                        }
                        
                return {
                    'status': 'success',
                    'response': '❌ Impossible de récupérer les documents demandés.'
                }

            # Handle Search
            entries = request.env['logistique.entry'].sudo().search([('invoice_number', 'ilike', query)])
            if not entries:
                entries = request.env['logistique.entry'].sudo().search([('bl_number', 'ilike', query)])
            if not entries:
                entries = request.env['logistique.entry'].sudo().search([('dum', 'ilike', query)])
            if not entries:
                entries = request.env['logistique.entry'].sudo().search([('lot', 'ilike', query)])

            if not entries:
                return {
                    'status': 'success',
                    'response': f"❌ Aucun dossier trouvé pour '{query}'."
                }

            text_response = f"📁 *Dossiers trouvés pour '{query}'* :\n\n"
            choices = []
            choice_idx = 1

            for entry in entries:
                bl = entry.bl_number or 'N/A'
                invoice = entry.invoice_number or 'N/A'
                week = entry.week or 'N/A'
                saisi_par = entry.saisi_par or 'N/A'
                text_response += f"🔹 *BL:* {bl} | *Facture:* {invoice} | *Week:* {week} | *Saisi par:* {saisi_par}\n"
                
                if not entry.document_ids:
                    text_response += "Aucun document attaché.\n\n"
                    continue
                
                for doc in entry.document_ids:
                    if not doc.file:
                        continue
                        
                    doc_type_dict = dict(doc._fields['document_type'].selection)
                    doc_name = doc_type_dict.get(doc.document_type, str(doc.document_type))
                    file_name = doc.file_name or f"{doc_name}.pdf"
                    
                    text_response += f"{choice_idx}. {file_name}\n"
                    choices.append(f"FETCH_DOC_SEARCH:logistique.entry.document:{doc.id}")
                    choice_idx += 1
                
                text_response += "\n"

            if not choices:
                return {
                    'status': 'success',
                    'response': text_response.strip()
                }

            text_response += "👉 *Répondez par le numéro du document que vous souhaitez télécharger.*"

            return {
                'status': 'multiple_choices',
                'message': text_response.strip(),
                'choices': choices
            }

        except Exception as e:
            _logger.error("Erreur API WhatsApp Dossier Search : %s", str(e))
            return {
                'status': 'error',
                'message': f"Erreur interne : {str(e)}"
            }

    def _generate_situation_report(self, week):
        entries = request.env['logistique.entry'].sudo().search([('week', '=ilike', week)])
        
        if not entries:
            return {
                'status': 'success',
                'response': f"📋 *ÉTAT DE CONTRÔLE : {week}*\n━━━━━━━━━━━━━━━━━━\nAucun dossier trouvé pour cette semaine."
            }
            
        on_port_entries = entries.filtered(lambda e: e.port_status == 'on_port')
        exited_entries = entries.filtered(lambda e: e.port_status == 'exited')
        closed_entries = entries.filtered(lambda e: e.status == 'closed')
        
        # 4- Nom personne en charge du week en cours
        saisi_par_list = [e.saisi_par for e in entries if e.saisi_par]
        saisi_par_str = ", ".join(set(saisi_par_list)) if saisi_par_list else "N/A"
        
        response = f"📋 *ÉTAT DE CONTRÔLE : {week}*\n"
        response += f"👤 *En charge* : {saisi_par_str}\n"
        response += "━━━━━━━━━━━━━━━━━━\n\n"
        
        # 1- Au port
        response += f"🚢 *1. AU PORT ({len(on_port_entries)} dossiers)*\n"
        for e in on_port_entries:
            tc_names = e.container_names or "N/A"
            eta_str = e.eta.strftime('%d/%m/%Y') if e.eta else "N/A"
            free_time = e.free_time or 0
            response += f"  • BL: {e.bl_number or 'N/A'}\n"
            response += f"    - TC: {tc_names}\n"
            response += f"    - ETA: {eta_str} | Franchise: {free_time}j\n"
            
        response += "\n"
        
        # 2- Sortie du port
        response += f"🚪 *2. SORTIE DU PORT ({len(exited_entries)} dossiers)*\n"
        for e in exited_entries:
            bad_str = e.bad_date.strftime('%d/%m/%Y') if e.bad_date else "N/A"
            exit_str = e.exit_date.strftime('%d/%m/%Y') if e.exit_date else "N/A"
            entry_str = e.entry_date.strftime('%d/%m/%Y') if e.entry_date else "N/A"
            
            # Chèques
            chq_series = [c.cheque_serie for c in e.cheque_ids if c.cheque_serie]
            chq_str = ", ".join(chq_series) if chq_series else "Aucun"
            
            thc = f"{e.thc_amount:,.2f}".replace(',', ' ')
            mag = f"{e.magasinage_amount:,.2f}".replace(',', ' ')
            sur = f"{e.surestarie_amount:,.2f}".replace(',', ' ')
            
            response += f"  • BL: {e.bl_number or 'N/A'}\n"
            response += f"    - Dates (BAD: {bad_str} | Sortie: {exit_str} | Entrée: {entry_str})\n"
            response += f"    - Frais: THC={thc} DH, Mag={mag} DH, Sur={sur} DH\n"
            response += f"    - Chèques: {chq_str}\n"
            
        response += "\n"
        
        # 3- Dossiers clôturés
        response += f"✅ *3. DOSSIERS CLÔTURÉS* : {len(closed_entries)}\n\n"
        
        # 5- Restant (Nombre TC au port)
        restant_tc = sum(e.container_count for e in on_port_entries)
        response += f"📦 *5. RESTANT* : {restant_tc} TC au port\n"
        
        return {
            'status': 'success',
            'response': response
        }
