import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsappDocumentSearchApi(http.Controller):

    @http.route('/api/whatsapp/dossier_search', type='json', auth='none', methods=['POST'], csrf=False)
    def handle_dossier_search(self, **kw):
        """
        Endpoint called by Whatsapp bridge to search a dossier and return attached documents.
        """
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

            # Search sequence (Invoice -> BL -> DUM -> Lot)
            # Find all matching entries for the first criteria that returns a match
            entries = request.env['logistique.entry'].sudo().search([('invoice_number', 'ilike', query)])
            
            if not entries:
                entries = request.env['logistique.entry'].sudo().search([('bl_number', 'ilike', query)])
                
            if not entries:
                entries = request.env['logistique.entry'].sudo().search(['|', ('prov_number', 'ilike', query), ('def_number', 'ilike', query)])
                
            if not entries:
                entries = request.env['logistique.entry'].sudo().search([('lot', 'ilike', query)])

            if not entries:
                return {
                    'status': 'success',
                    'message': f"❌ Aucun dossier trouvé pour '{query}'."
                }

            text_response = f"📁 *Dossiers trouvés pour '{query}'* :\n\n"
            documents_to_send = []

            for idx, entry in enumerate(entries):
                bl = entry.bl_number or 'N/A'
                invoice = entry.invoice_number or 'N/A'
                text_response += f"🔹 *BL:* {bl} | *Facture:* {invoice}\n"
                
                if not entry.document_ids:
                    text_response += "Aucun document attaché.\n\n"
                    continue
                
                text_response += "Documents :\n"
                for doc_idx, doc in enumerate(entry.document_ids):
                    # Get translated/readable document type name
                    doc_type_dict = dict(doc._fields['document_type'].selection)
                    doc_name = doc_type_dict.get(doc.document_type, str(doc.document_type))
                    
                    file_name = doc.file_name or f"{doc_name}.pdf"
                    text_response += f"{doc_idx + 1}. {file_name}\n"
                    
                    if doc.file:
                        # doc.file is binary base64 stored as bytes in py3
                        base64_str = doc.file.decode('utf-8') if isinstance(doc.file, bytes) else doc.file
                        documents_to_send.append({
                            'name': file_name,
                            'base64': base64_str,
                            'mimetype': 'application/pdf'
                        })
                text_response += "\n"

            return {
                'status': 'success',
                'message': text_response.strip(),
                'documents_to_send': documents_to_send
            }

        except Exception as e:
            _logger.error("Erreur API WhatsApp Dossier Search : %s", str(e))
            return {
                'status': 'error',
                'message': f"Erreur interne : {str(e)}"
            }
