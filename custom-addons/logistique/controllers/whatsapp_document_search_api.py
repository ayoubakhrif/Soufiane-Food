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

            # Handle Cheques Fetch
            if 'FETCH_CHEQUES:' in query:
                parts = [p for p in query.split('|') if p.startswith('FETCH_CHEQUES:')]
                if parts:
                    entry_id = int(parts[0].split(':')[1])
                    entry = request.env['logistique.entry'].sudo().browse(entry_id)
                    if entry.exists() and entry.cheque_ids:
                        series = [c.cheque_serie for c in entry.cheque_ids if c.cheque_serie]
                        phys_cheques = request.env['finance.cheque.physical'].sudo().search([('name', 'in', series)])
                        
                        pdf_data_list = []
                        for chq in phys_cheques:
                            if chq.cheque_copy_pdf:
                                pdf_data_list.append(chq.cheque_copy_pdf)
                            elif chq.chq_vide_pdf:
                                pdf_data_list.append(chq.chq_vide_pdf)
                                
                        if pdf_data_list:
                            import base64
                            import io
                            
                            output = io.BytesIO()
                            try:
                                from PyPDF2 import PdfReader, PdfWriter
                                writer = PdfWriter()
                                for b64_pdf in pdf_data_list:
                                    try:
                                        pdf_bytes = base64.b64decode(b64_pdf)
                                        reader = PdfReader(io.BytesIO(pdf_bytes))
                                        for page in reader.pages:
                                            writer.add_page(page)
                                    except Exception as e:
                                        _logger.error("Error merging PDF (v3): %s", str(e))
                                writer.write(output)
                            except ImportError:
                                from PyPDF2 import PdfFileReader, PdfFileWriter
                                writer = PdfFileWriter()
                                for b64_pdf in pdf_data_list:
                                    try:
                                        pdf_bytes = base64.b64decode(b64_pdf)
                                        reader = PdfFileReader(io.BytesIO(pdf_bytes))
                                        for page_num in range(reader.getNumPages()):
                                            writer.addPage(reader.getPage(page_num))
                                    except Exception as e:
                                        _logger.error("Error merging PDF (v1/v2): %s", str(e))
                                writer.write(output)
                            
                            merged_b64 = base64.b64encode(output.getvalue()).decode('utf-8')
                            
                            return {
                                'status': 'success',
                                'files': [{
                                    'file_name': f"Cheques_BL_{entry.bl_number or 'Inconnu'}.pdf",
                                    'base64': merged_b64,
                                    'mimetype': 'application/pdf',
                                    'caption': f"Voici les chèques fusionnés pour le BL *{entry.bl_number or 'Inconnu'}*."
                                }]
                            }
                        else:
                            return {
                                'status': 'success',
                                'response': '❌ Aucun chèque physique (PDF) trouvé dans la Finance pour ce dossier.'
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
                
                if entry.cheque_ids:
                    text_response += f"{choice_idx}. Chèques (Fusionnés)\n"
                    choices.append(f"FETCH_CHEQUES:{entry.id}")
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
