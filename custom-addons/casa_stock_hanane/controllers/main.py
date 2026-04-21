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

        # --- NEW: Check for General Stock Report trigger (with more flexibility for typos) ---
        general_triggers = [
            'stock général', 'stock general', 'situation générale', 'situation generale', 
            'stock total', 'stok general', 'stok génial', 'stok genial', 'total stock'
        ]
        message_clean = message_text.lower().strip()
        
        # 1. Quick check with hardcoded list
        is_general = any(trigger in message_clean for trigger in general_triggers)
        
        # 3. Call OpenAI to extract product name (with a rule for Global Report)
        openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not openai_key:
            return {'status': 'error', 'message': 'OpenAI API key not configured in Odoo'}

        # Fetch all article names to guide the AI
        all_articles = request.env['company.article'].sudo().search([])
        article_names_list = list(set([a.name for a in all_articles if a.name]))
        
        # We call AI if it's not obviously a general trigger or if we want extra flexibility
        all_aliases = request.env['casa_hanane.article.alias'].sudo().search([])
        darija_aliases_list = [f"{a.name} -> {a.article_id.name}" for a in all_aliases if a.article_id]
        
        extracted_str = self._extract_product_name(message_text, openai_key, article_names_list, darija_aliases_list)

        # 2. Check if AI identified it as a global report request
        if is_general or (extracted_str and extracted_str.upper() == 'GLOBAL_STOCK_REPORT'):
            report_action = request.env.ref('casa_stock_hanane.action_report_casa_stock_general').sudo()
            dummy_record = request.env['casa_hanane.stock.stock'].sudo().search([('quantity', '>', 0)], limit=1)
            
            if not dummy_record:
                return {'status': 'not_found', 'message': "Désolé, il n'y a actuellement aucun article en stock pour générer le rapport général."}
            
            pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf('casa_stock_hanane.action_report_casa_stock_general', res_ids=dummy_record.ids)
            from odoo import fields
            return {
                'status': 'success',
                'message': "Information : J'ai identifié une demande de situation globale.\nVoici l'état consolidé du stock (Quantités, Tonnages et Valeurs).",
                'pdf_base64': base64.b64encode(pdf_content).decode('utf-8'),
                'pdf_name': f"Situation_Generale_Stock_{fields.Date.today()}.pdf"
            }

        # Step 1: Check for an exact name match (after confirming it's not a global report)
        articles = request.env['company.article'].sudo().search([('name', '=ilike', message_text)])
        
        final_extracted_str = message_text
        
        # Step 2: If no single exact match
        if len(articles) != 1:
            # Check for manual aliases matching the message words
            words = [w.strip() for w in message_text.split() if len(w.strip()) > 2]
            for word in words:
                alias_matches = request.env['casa_hanane.article.alias'].sudo().search([('name', 'ilike', word)])
                if alias_matches:
                    articles |= alias_matches.mapped('article_id')

            # Step 3: Use OpenAI for intelligent extraction
            all_aliases = request.env['casa_hanane.article.alias'].sudo().search([])
            darija_aliases_list = [f"{a.name} -> {a.article_id.name}" for a in all_aliases if a.article_id]
            
            extracted_str = self._extract_product_name(message_text, openai_key, article_names_list, darija_aliases_list)

            if extracted_str and extracted_str.lower() != 'none':
                final_extracted_str = extracted_str
                extracted_list = [name.strip() for name in extracted_str.split(',')]
                ai_domain = []
                for name in extracted_list:
                    ai_domain.append(('name', 'ilike', name))
                    # Also lookup by alias in case AI returns an alias keyword
                    alias_ids = request.env['casa_hanane.article.alias'].sudo().search([('name', 'ilike', name)]).mapped('article_id').ids
                    if alias_ids:
                        ai_domain.append(('id', 'in', alias_ids))
                
                if ai_domain:
                    for i in range(len(ai_domain) - 1):
                        ai_domain.insert(0, '|')
                    articles |= request.env['company.article'].sudo().search(ai_domain)
        
        if not articles:
            return {'status': 'not_found', 'message': f"Aucun article trouvé pour la demande: '{final_extracted_str}'."}

        products = request.env['casa_hanane.product'].sudo().search([('article_id', 'in', articles.ids)])
        
        # Check stock globally for these products (Strictly positive stock)
        stock_records = request.env['casa_hanane.stock.stock'].sudo().search([
            ('product_id', 'in', products.ids), 
            ('quantity', '>', 0)
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
            pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf('casa_stock_hanane.action_report_casa_stock_product', res_ids=stock_for_pdf.ids)
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

    def _extract_product_name(self, text, api_key, article_names_list, darija_aliases=None):
        """Use OpenAI to extract the product name from a natural language sentence."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Convert list to string for the prompt
        db_names = ", ".join(article_names_list) if article_names_list else "Aucun article disponible"
        synonyms = "\n".join(darija_aliases) if darija_aliases else "Aucun synonyme défini."
        
        prompt = (
            "Tu es un assistant logistique. Ta tâche est d'identifier le nom correct de l'article demandé.\n"
            "Voici la liste stricte des articles de la base de données :\n"
            f"[{db_names}]\n\n"
            "Voici un dictionnaire de synonymes/Darija spécifique à l'entreprise pour t'aider :\n"
            f"{synonyms}\n\n"
            "Message WhatsApp : " + text + "\n\n"
            "Règles strictes :\n"
            "1. Si l'utilisateur demande une situation globale, le stock général ou le stock total (même avec des fautes comme 'stok genial'), réponds UNIQUEMENT 'GLOBAL_STOCK_REPORT'.\n"
            "2. Sinon, identifie le nom de l'article. Utilise tes connaissances générales pour traduire les mots (ex: 'ibzar' -> 'Poivre'). Si tu ne trouves pas ou si tu as un doute, réfère-toi au dictionnaire de synonymes ci-dessus.\n"
            "3. Si la demande est très précise (ex: 'Poivre B1'), renvoie le nom exact.\n"
            "4. Si la demande est globale par type (ex: 'poivre'), renvoie UNIQUEMENT LE TERME COURT (ex: 'Poivre').\n"
            "Retourne UNIQUEMENT le mot trouvé (ou GLOBAL_STOCK_REPORT). Si aucun ne correspond, réponds 'None'."
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
