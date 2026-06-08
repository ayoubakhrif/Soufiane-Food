import json
import logging
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

            # Handle Document Fetch
            if query.startswith('FETCH_DOC_SEARCH:'):
                parts = query.split(':')
                if len(parts) == 3:
                    doc_model = parts[1]
                    doc_id = int(parts[2])
                    doc = request.env[doc_model].sudo().browse(doc_id)
                    if doc.exists() and doc.file:
                        doc_type_dict = dict(doc._fields['document_type'].selection)
                        doc_name = doc_type_dict.get(doc.document_type, str(doc.document_type))
                        file_name = doc.file_name or f"{doc_name}.pdf"
                        
                        base64_str = doc.file.decode('utf-8') if isinstance(doc.file, bytes) else doc.file
                        return {
                            'status': 'success',
                            'files': [{
                                'file_name': file_name,
                                'base64': base64_str,
                                'mimetype': 'application/pdf',
                                'caption': f"Voici le document *{file_name}* demandé."
                            }]
                        }
                return {
                    'status': 'success',
                    'response': '❌ Impossible de récupérer le document demandé.'
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
