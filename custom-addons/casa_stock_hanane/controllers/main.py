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

        # Fetch all article names to guide the AI
        all_articles = request.env['company.article'].sudo().search([])
        article_names_list = list(set([a.name for a in all_articles if a.name]))

        product_name = self._extract_product_name(message_text, openai_key, article_names_list)
        if not product_name or product_name.lower() == 'none':
            return {'status': 'not_found', 'message': "Désolé, je n'ai pas pu identifier le produit dans votre message."}

        # 4. Search for Products (by name or article name)
        products = request.env['casa_hanane.product'].sudo().search([
            '|',
            ('name', 'ilike', product_name),
            ('article_id.name', 'ilike', product_name)
        ])
        
        if not products:
            return {'status': 'not_found', 'message': f"Aucun produit ou article trouvé pour '{product_name}' dans la base de données."}

        # 5. Get stock records and generate PDF
        stock_records = request.env['casa_hanane.stock.stock'].sudo().search([
            ('product_id', 'in', products.ids), 
            ('quantity', '!=', 0)
        ])
        
        if not stock_records:
            return {'status': 'not_found', 'message': f"Aucun stock disponible pour les variantes de '{product_name}'."}

        # 6. Generate PDF Report
        report_action = request.env['ir.actions.report'].sudo()
        pdf_content, _ = report_action._render_qweb_pdf('casa_stock_hanane.action_report_casa_stock_product', res_ids=stock_records.ids)
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

        return {
            'status': 'success',
            'product_name': product_name,
            'pdf_base64': pdf_base64,
            'file_name': f"Rapport_Stock_{product_name.replace(' ', '_')}.pdf"
        }

    def _extract_product_name(self, text, api_key, article_names_list):
        """Use OpenAI to extract the product name from a natural language sentence."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Convert list to string for the prompt
        db_names = ", ".join(article_names_list) if article_names_list else "Aucun article disponible"
        
        prompt = (
            "Tu es un assistant logistique. Ta tâche est de trouver l'article de la base de données qui correspond à la demande WhatsApp.\n"
            "Voici la liste stricte des articles existant en base de données :\n"
            f"[{db_names}]\n\n"
            "Message WhatsApp : " + text + "\n\n"
            "Trouve l'article de la liste qui correspond le mieux au message, en tenant compte des fautes d'orthographe (ex: 'Popcurn' -> 'Popcorn', ou 'amendes' -> 'Amande'). "
            "Retourne UNIQUEMENT le nom de cet article exact de la liste (au caractère près), rien d'autre. Si aucun article ne correspond, réponds 'None'."
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
