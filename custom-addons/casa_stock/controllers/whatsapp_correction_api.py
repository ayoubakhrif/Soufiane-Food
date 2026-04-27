import logging
import json
from odoo import http, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppCorrectionController(http.Controller):

    @http.route('/api/whatsapp/casa_correction', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_casa_correction_handler(self, **kwargs):
        """Webhook for Casa Stock correction bot."""
        # Force database session
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        # 1. API Key Verification
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'default-secret-key')
        
        if not api_key or api_key != expected_api_key:
            _logger.warning("Unauthorized access attempt to WhatsApp Casa Correction API")
            return {'status': 'error', 'message': 'Unauthorized'}

        # 2. Extract Data
        data = kwargs
        message_text = data.get('message', '').strip()
        group_id = data.get('group_id', '')
        sender = data.get('sender', 'unknown')

        if not message_text:
            return {'status': 'error', 'message': 'Empty message'}

        # 3. Target Group Verification
        # Nouveau groupe de correction : 120363049891261462@g.us
        CORRECTION_GROUP_ID = '120363049891261462@g.us'
        
        if group_id != CORRECTION_GROUP_ID:
            _logger.info(f"Ignoring request from group {group_id} in Casa Correction Agent")
            return {'status': 'ignored', 'message': 'This agent only handles the specific Correction Group.'}

        # 4. Process via Chatbot Engine
        try:
            Chatbot = request.env['casa.stock.chatbot'].sudo()
            response_text = Chatbot.process_message(message_text, sender=group_id)
            
            if response_text:
                return {'status': 'success', 'response': response_text}
            else:
                return {'status': 'ignored'}
                
        except Exception as e:
            _logger.error(f"Error in Casa Correction Chatbot: {str(e)}")
            return {'status': 'error', 'message': 'Internal server error'}
