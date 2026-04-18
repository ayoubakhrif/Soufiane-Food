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

        extracted_str = self._extract_product_name(message_text, openai_key, article_names_list)
        if not extracted_str or extracted_str.lower() == 'none':
            return {'status': 'not_found', 'message': "Désolé, je n'ai pas pu identifier le produit dans votre message."}

        # Handle comma-separated list of matches from OpenAI
        extracted_list = [name.strip() for name in extracted_str.split(',')]
        
        # Determine all corresponding articles
        articles = request.env['company.article'].sudo().search([('name', 'in', extracted_list)])
        if not articles:
            return {'status': 'not_found', 'message': f"Aucun article trouvé pour la demande: '{extracted_str}'."}

        products = request.env['casa_hanane.product'].sudo().search([('article_id', 'in', articles.ids)])
        
        # Check stock globally for these products
        stock_records = request.env['casa_hanane.stock.stock'].sudo().search([
            ('product_id', 'in', products.ids), 
            ('quantity', '!=', 0)
        ])
        
        if not stock_records:
            return {'status': 'not_found', 'message': f"Aucun stock disponible pour '{extracted_str}'."}

        # Which distinct articles actually have positive stock?
        articles_in_stock = stock_records.mapped('product_id.article_id')
        
        if len(articles_in_stock) == 0:
            return {'status': 'not_found', 'message': "Aucun stock disponible actuellement."}
            
        elif len(articles_in_stock) == 1:
            # ONLY ONE VARIETY HAS STOCK -> GENERATE PDF
            stock_for_pdf = stock_records.filtered(lambda r: r.product_id.article_id.id == articles_in_stock[0].id)
            report_action = request.env['ir.actions.report'].sudo()
            pdf_content, _ = report_action._render_qweb_pdf('casa_stock_hanane.action_report_casa_stock_product', res_ids=stock_for_pdf.ids)
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            return {
                'status': 'success',
                'product_name': articles_in_stock[0].name,
                'pdf_base64': pdf_base64,
                'file_name': f"Rapport_Stock_{articles_in_stock[0].name.replace(' ', '_')}.pdf"
            }
            
        else:
            # MORE THAN 1 VARIETY HAS STOCK => PROMPT THE USER WITH NUMBERS!
            varieties = [a.name for a in articles_in_stock]
            choices_text = "Veuillez choisir le produit que vous voulez consulter :\n"
            for i, v in enumerate(varieties, 1):
                choices_text += f"{i}- {v}\n"
                
            return {
                'status': 'multiple_choices',
                'message': choices_text,
                'choices': varieties
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
            "Tu es un assistant logistique. Ta tâche est de trouver LES articles correspondants à la demande WhatsApp.\n"
            "Voici la liste stricte des articles existant en base de données :\n"
            f"[{db_names}]\n\n"
            "Message WhatsApp : " + text + "\n\n"
            "Règles strictes :\n"
            "1. Si le message (même mal orthographié, ex: 'popcurn' au lieu de 'Popcorn') correspond à une famille générique (ex: 'Poivre', 'Maïs'), liste TOUS les articles correspondants de la liste (ex: 'Poivre B1, Poivre Asta, Poivre blanc').\n"
            "2. Si le message demande un produit précis, renvoie juste ce nom.\n"
            "Retourne UNIQUEMENT les noms exacts séparés par des virgules (sans guillemets, sans aucun autre texte). Si aucun ne correspond, réponds 'None'."
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
