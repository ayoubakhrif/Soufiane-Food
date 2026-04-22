import base64
import logging
import requests
from odoo import http, SUPERUSER_ID, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppDouaneController(http.Controller):

    @http.route('/api/whatsapp/douane', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_douane_handler(self, **kwargs):
        # Force database session
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        # 1. API Key Verification
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'whatsapp_direct_quantity')
        
        if not api_key or api_key != expected_api_key:
            _logger.warning("Unauthorized access attempt to WhatsApp Douane API")
            return {'status': 'error', 'message': 'Unauthorized'}

        # 2. Extract Data
        try:
            data = kwargs
            message_text = data.get('message', '').strip()
            group_id = data.get('group_id', '')
        except Exception as e:
            return {'status': 'error', 'message': f'Invalid JSON: {str(e)}'}

        if not message_text:
            return {'status': 'error', 'message': 'Empty message'}

        # 3. Target Group Verification
        DOUANE_GROUP_ID = '120363406635335778@g.us'
        if group_id != DOUANE_GROUP_ID:
            _logger.info(f"Ignoring request from group {group_id} in Douane Agent")
            return {'status': 'ignored', 'message': 'This agent only handles the Douane Group.'}

        # 4. Extract Reference using OpenAI
        openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not openai_key:
            return {'status': 'error', 'message': 'OpenAI API key not configured'}

        reference = self._extract_reference(message_text, openai_key)
        
        if not reference or reference.upper() == 'IGNORE':
            _logger.info(f"Ignoring off-topic message in Douane: {message_text}")
            return {'status': 'ignored'}

        if reference.upper() == 'NONE':
            return {'status': 'not_found', 'message': "Désolé, je n'ai pas pu identifier de référence DUM ou BL dans votre message."}

        # 5. Search for Entry
        # A. Try by DUM
        entry = request.env['logistique.entry'].sudo().search([('dum', '=', reference)], limit=1)
        
        # B. Try by BL if DUM fails
        if not entry:
            entry = request.env['logistique.entry'].sudo().search([('bl_number', '=', reference)], limit=1)
            
        # C. Try with partial match if no exact match (optional but helpful)
        if not entry:
            entry = request.env['logistique.entry'].sudo().search([('dum', 'ilike', reference)], limit=1)
        if not entry:
            entry = request.env['logistique.entry'].sudo().search([('bl_number', 'ilike', reference)], limit=1)

        if not entry:
            return {'status': 'not_found', 'message': f"Aucun dossier trouvé pour la référence : '{reference}'."}

        # 6. Retrieve Documents (Type 'dum')
        docs = request.env['douane.document'].sudo().search([
            ('entry_id', '=', entry.id),
            ('type', '=', 'dum')
        ])

        if not docs:
            ref_display = entry.dum or entry.bl_number
            return {'status': 'not_found', 'message': f"Dossier trouvé (BL: {entry.bl_number}), mais aucun document PDF de type 'DUM' n'est attaché."}

        # 7. Prepare Success Response
        files = []
        for doc in docs:
            if doc.file:
                files.append({
                    'pdf_base64': doc.file.decode('utf-8'),
                    'file_name': doc.file_name or f"DUM_{entry.dum or entry.bl_number}.pdf"
                })

        if not files:
             return {'status': 'not_found', 'message': "Le document existe mais le fichier est vide."}

        # Return the identifier and the list of files
        # product_name is used by the bridge as a default name for the caption
        return {
            'status': 'success',
            'product_name': entry.dum or entry.bl_number,
            'files': files
        }

    def _extract_reference(self, text, api_key):
        """Use OpenAI to extract DUM or BL reference."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        prompt = (
            "Tu es un assistant logistique. Ta tâche est d'identifier la référence d'un dossier mentionnée dans un message WhatsApp.\n"
            "Il peut s'agir :\n"
            "- D'un numéro de DUM (ex: 12345/2026, 610/2025)\n"
            "- D'un numéro de BL (ex: MEDUT7846505, MSCU1234567)\n\n"
            "Message WhatsApp : " + text + "\n\n"
            "Règles :\n"
            "1. Identifie la référence la plus probable.\n"
            "2. Retourne uniquement la référence (ex: '610/2026').\n"
            "3. IMPORTANT : Si le message ne contient que des salutations ou emojis, réponds 'IGNORE'.\n"
            "4. Si tu ne trouves rien de ressemblant à une référence, réponds 'None'.\n"
            "Retourne UNIQUEMENT le résultat."
        )
        data = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            _logger.error(f"OpenAI Douane Extraction Error: {str(e)}")
            return None
