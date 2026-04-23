import base64
import json
import logging
import requests
import traceback
from datetime import datetime
from odoo import http, SUPERUSER_ID, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppSortieController(http.Controller):

    @http.route('/api/whatsapp/sortie', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_sortie_handler(self, **kwargs):
        # Force database session
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        # 1. API Key Verification
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'default-secret-key')
        
        if not api_key or api_key != expected_api_key:
            _logger.warning("Unauthorized access attempt to WhatsApp Sortie API")
            return {'status': 'error', 'message': 'Unauthorized'}

        # 2. Extract Data
        data = kwargs
        message_text = data.get('message', '').strip()
        group_id = data.get('group_id', '')

        if not message_text:
            return {'status': 'error', 'message': 'Empty message'}

        # 3. Target Group Verification
        SORTIE_GROUP_ID = '120363424919316319@g.us'
        if group_id != SORTIE_GROUP_ID:
            _logger.info(f"Ignoring request from group {group_id} in Sortie Agent")
            return {'status': 'ignored', 'message': 'This agent only handles the Sortie Group.'}

        # 4. FAST TRACK: Search in Article + Aliases first (Case-insensitive)
        exact_article = request.env['company.article'].sudo().search([
            '|', ('display_name', '=ilike', message_text), ('alias_ids.name', '=ilike', message_text)
        ], limit=1)
        
        if exact_article:
            casa_products = request.env['casa.product'].sudo().search([('article_id', '=', exact_article.id)])
            if casa_products:
                return self._generate_report_response(product_ids=casa_products.ids)

        # 5. Process Message via OpenAI if no exact match
        openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not openai_key:
            return {'status': 'error', 'message': 'OpenAI API key not configured'}

        # Fetch product names and aliases for AI (larger samples)
        all_articles = request.env['company.article'].sudo().search([], limit=200)
        article_names = [a.display_name for a in all_articles if a.display_name]
        
        all_aliases = request.env['company.article.alias'].sudo().search([], limit=100)
        alias_list = [f"{a.name} -> {a.article_id.display_name}" for a in all_aliases if a.article_id]

        analysis = self._analyze_intent(message_text, openai_key, article_names, alias_list)
        
        if not analysis or analysis.get('intent') == 'IGNORE':
            # Last chance: if it's a single word, maybe it's a product OpenAI doesn't know
            if len(message_text.split()) == 1 and len(message_text) > 3:
                 # Try a broad search
                 article = request.env['company.article'].sudo().search([
                    '|', ('display_name', 'ilike', message_text), ('alias_ids.name', 'ilike', message_text)
                 ], limit=1)
                 if article:
                     casa_products = request.env['casa.product'].sudo().search([('article_id', '=', article.id)])
                     if casa_products:
                         return self._generate_report_response(product_ids=casa_products.ids)
            
            _logger.info(f"Ignoring message in Sortie: {message_text}")
            return {'status': 'ignored'}

        if analysis.get('intent') == 'NONE':
            return {'status': 'not_found', 'message': "Desole, je n'ai pas pu identifier de date ou de produit dans votre message."}

        # 5. Handle Date Intent
        if analysis.get('intent') == 'DATE':
            date_str = analysis.get('value')
            try:
                # Value should be in YYYY-MM-DD
                return self._generate_report_response(date_filter=date_str)
            except Exception as e:
                _logger.error(f"Error generating date report: {str(e)}\n{traceback.format_exc()}")
                return {'status': 'error', 'message': "Erreur lors de la generation du rapport par date."}

        # 6. Handle Product Intent
        if analysis.get('intent') == 'PRODUCT':
            product_name = analysis.get('value')
            # Find the company article
            article = request.env['company.article'].sudo().search([
                '|', ('display_name', '=', product_name), ('alias_ids.name', '=', product_name)
            ], limit=1)
            
            if not article:
                return {'status': 'not_found', 'message': f"L'article '{product_name}' n'est pas reconnu."}
            
            # Find linked casa.product records
            casa_products = request.env['casa.product'].sudo().search([('article_id', '=', article.id)])
            if not casa_products:
                return {'status': 'not_found', 'message': f"Aucun produit 'Casa' lie a l'article '{article.display_name}'."}
            
            return self._generate_report_response(product_ids=casa_products.ids)

        return {'status': 'error', 'message': 'Intent identification failed.'}

    def _generate_report_response(self, date_filter=None, product_ids=None):
        """Helper to render PDF and return response."""
        # Check if records exist
        domain = [('state', '=', 'done')]
        if date_filter:
            domain.append(('date', '=', date_filter))
        if product_ids:
            domain.append(('product_id', 'in', product_ids))
            
        count = request.env['casa.stock.exit'].sudo().search_count(domain)
        if count == 0:
            msg = "Aucune sortie confirme trouvee pour cette demande."
            if date_filter:
                msg = f"Aucune sortie confirme pour le {datetime.strptime(date_filter, '%Y-%m-%d').strftime('%d/%m/%Y')}."
            return {'status': 'response', 'response': msg}

        # Render PDF
        data = {'date_filter': date_filter, 'product_ids': product_ids}
        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'casa_stock.action_report_casa_stock_exit', 
            res_ids=request.env['casa.stock.exit'].sudo().search(domain, limit=1).ids, # Dummy recordset
            data=data
        )
        
        from odoo import fields
        file_name = f"Sorties_{fields.Date.today()}.pdf"
        if date_filter:
            file_name = f"Sorties_{date_filter}.pdf"
            
        return {
            'status': 'success',
            'pdf_base64': base64.b64encode(pdf_content).decode('utf-8'),
            'file_name': file_name
        }

    def _analyze_intent(self, text, api_key, article_names, alias_list):
        """Use OpenAI to determine if message is a Date or a Product."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        today = datetime.now().strftime('%Y-%m-%d')
        articles_str = ", ".join(article_names[:100]) # Sample for brevity
        aliases_str = "\n".join(alias_list[:50])

        prompt = (
            "Tu es un assistant logistique pour une societe agroalimentaire. Ta tâche est d'analyser le message de l'utilisateur pour extraire soit une DATE, soit un PRODUIT.\n\n"
            f"Nous sommes aujourd'hui le : {today}.\n\n"
            "Voici une liste d'articles connus (peut etre incomplete) :\n"
            f"[{articles_str}]\n"
            "Et quelques alias Darija :\n"
            f"{aliases_str}\n\n"
            "Message utilisateur : " + text + "\n\n"
            "Règles :\n"
            "1. DATE : si l'utilisateur demande une date (ex: 'aujourd'hui', 'hier', '23/04', 'lundi'), renvoie {\"intent\": \"DATE\", \"value\": \"YYYY-MM-DD\"}.\n"
            "2. PRODUCT : si l'utilisateur mentionne un aliment, une epice (ex: 'skenjbir', 'gingembre', 'poivre'), ou un article de la liste, renvoie {\"intent\": \"PRODUCT\", \"value\": \"Nom de l'Article\"}.\n"
            "3. IGNORE : uniquement pour les messages totalement hors sujet (ex: 'ca va ?', 'ok', emojis seuls).\n"
            "IMPORTANT : Ne sois pas trop restrictif. Si le mot ressemble a un produit alimentaire, c'est un PRODUCT.\n"
            "Retourne UNIQUEMENT le JSON."
        )
        
        data = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "response_format": { "type": "json_object" }
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            return json.loads(content)
        except Exception as e:
            _logger.error(f"OpenAI Intent Analysis Error: {str(e)}")
            return None
