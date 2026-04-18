import base64
import json
import logging
import requests
from odoo import http, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppStockController(http.Controller):

    @http.route('/whatsapp/health', type='http', auth='none', methods=['GET'], csrf=False)
    def whatsapp_health(self):
        return "Odoo API is ALIVE"

    @http.route('/api/whatsapp/stock', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_stock(self, **kwargs):
        # En mode auth='none', on force la base de données
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        # 1. Verification of API Key
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'default-secret-key')
        
        if not api_key or api_key != expected_api_key:
            _logger.warning("Unauthorized access attempt to WhatsApp API")
            return {'status': 'error', 'message': 'Unauthorized'}

        # 2. Extract data from request
        try:
            data = kwargs
            message_text = data.get('message', '')
            group_id = data.get('group_id', '')
        except Exception as e:
            return {'status': 'error', 'message': f'Invalid JSON: {str(e)}'}

        if not message_text:
            return {'status': 'error', 'message': 'Empty message'}

        # 3. Call OpenAI to extract product name
        openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not openai_key:
            return {'status': 'error', 'message': 'OpenAI API key not configured in Odoo'}

        product_name = self._extract_product_name(message_text, openai_key)
        if not product_name or product_name.lower() == 'none':
            return {'status': 'not_found', 'message': "Désolé, je n'ai pas pu identifier le produit dans votre message."}

        # 4. Search for product in Odoo (Hanane Stock)
        product = request.env['casa_hanane.product'].sudo().search([('name', 'ilike', product_name)], limit=1)
        if not product:
            return {'status': 'not_found', 'message': f"Produit '{product_name}' non trouvé dans la base de données."}

        # 5. Get stock records and generate PDF
        stock_records = request.env['casa_hanane.stock.stock'].sudo().search([('product_id', '=', product.id), ('quantity', '!=', 0)])
        if not stock_records:
            return {'status': 'not_found', 'message': f"Aucun stock disponible pour '{product.name}'."}

        # 6. Generate PDF Report
        report = request.env.ref('casa_stock_hanane.action_report_casa_stock_product').sudo()
        pdf_content, _ = report._render_qweb_pdf(stock_records.ids)
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

        return {
            'status': 'success',
            'product_name': product.name,
            'pdf_base64': pdf_base64,
            'file_name': f"Rapport_Stock_{product.name.replace(' ', '_')}.pdf"
        }

    def _extract_product_name(self, text, api_key):
        """Use OpenAI to extract the product name from a natural language sentence."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        prompt = (
            "Tu es un assistant logistique. Ta tâche est d'extraire uniquement le nom du produit mentionné "
            "dans un message WhatsApp demandant le stock. "
            "Exemple: 'Stock de Pomme Gala' -> 'Pomme Gala'. "
            "Si aucun produit n'est identifié, réponds 'None'. "
            "Message : " + text
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
            _logger.error(f"OpenAI Error: {str(e)}")
            return None
