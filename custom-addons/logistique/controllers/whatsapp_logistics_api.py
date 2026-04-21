import base64
import json
import logging
import requests
from datetime import date
from odoo import http, SUPERUSER_ID, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppLogisticsController(http.Controller):

    @http.route('/api/whatsapp/logistics', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_logistics_report(self, **kwargs):
        # Force database session
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        # 1. API Key Verification
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'default-secret-key')
        
        if not api_key or api_key != expected_api_key:
            _logger.warning("Unauthorized access attempt to WhatsApp Logistics API")
            return {'status': 'error', 'message': 'Unauthorized'}

        # 2. Extract Data
        data = kwargs
        message_text = data.get('message', '').strip()
        group_id = data.get('group_id', '')

        if not message_text:
            return {'status': 'error', 'message': 'Empty message'}

        # 3. Target Group Verification
        LOGISTICS_GROUP_ID = '120363427755410654@g.us'
        if group_id != LOGISTICS_GROUP_ID:
            _logger.info(f"Ignoring request from group {group_id} in Logistics Agent")
            return {'status': 'ignored', 'message': 'This agent only handles the Logistics Group.'}

        # 4. Search for Article
        # A. Direct Search
        articles = request.env['logistique.article'].sudo().search([('name', '=ilike', message_text)])
        
        # B. AI Fallback if no result
        if not articles:
            openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
            if openai_key:
                # Fetch article names for AI guidance
                all_article_names = request.env['logistique.article'].sudo().search([]).mapped('name')
                extracted_name = self._extract_product_name(message_text, openai_key, all_article_names)
                
                if extracted_name and extracted_name.lower() != 'none':
                    articles = request.env['logistique.article'].sudo().search([('name', 'ilike', extracted_name)])

        if not articles:
            return {'status': 'not_found', 'message': "Désolé, je n'ai pas trouvé cet article dans la logistique."}

        # 5. Handle Multiple Choices
        if len(articles) > 1:
            # Check for exact case-insensitive match among results
            exact_match = articles.filtered(lambda a: a.name.lower() == message_text.lower())
            if exact_match:
                articles = exact_match[0]
            else:
                choices = [a.name for a in articles]
                choices_text = "Plusieurs articles trouvés. Veuillez préciser :\n"
                for i, name in enumerate(choices, 1):
                    choices_text += f"{i}- {name}\n"
                return {
                    'status': 'multiple_choices',
                    'message': choices_text,
                    'choices': choices
                }

        # 6. Process Unique Article
        article = articles[0]
        entries = request.env['logistique.entry'].sudo().search([
            ('article_id', '=', article.id),
            ('port_status', '=', 'on_port')
        ], order='eta asc')

        if not entries:
            return {
                'status': 'response',
                'response': f"📋 *Logistique : {article.name}*\n\n✅ Aucun conteneur en cours pour cet article (tous sont sortis ou aucun dossier existant)."
            }

        # 7. Group entries by ETA
        today = date.today()
        at_port = []
        upcoming = {} # eta_string -> container_count

        for entry in entries:
            cnt = entry.container_count or 0
            if entry.eta and entry.eta < today:
                at_port.append(entry)
            else:
                eta_str = entry.eta.strftime('%d/%m/%Y') if entry.eta else "Date inconnue"
                upcoming[eta_str] = upcoming.get(eta_str, 0) + cnt

        # 8. Format Response
        response = f"🚢 *LOGISTIQUE - {article.name.upper()}*\n"
        response += f"━━━━━━━━━━━━━━━━━━\n\n"

        # Section: At Port
        if at_port:
            total_at_port = sum(e.container_count for e in at_port)
            response += f"⚓ *DÉJÀ SUR PORT ({total_at_port} conteneurs)*\n"
            for entry in at_port:
                eta_val = entry.eta.strftime('%d/%m/%Y') if entry.eta else "N/A"
                response += f"• BL {entry.bl_number or 'Inconnu'} : *{entry.container_count}* cont.(ETA: {eta_val})\n"
            response += "\n"

        # Section: Upcoming
        if upcoming:
            response += f"📅 *ARRIVAGES À VENIR*\n"
            for eta_date, count in upcoming.items():
                response += f"• Le *{eta_date}* : *{count}* conteneurs\n"
        elif not at_port:
            response += "⚠️ Aucun conteneur en attente détecté.\n"

        response += "\n_Statut : On Port uniquement_"

        return {
            'status': 'response',
            'response': response
        }

    def _extract_product_name(self, text, api_key, article_names):
        """Use OpenAI to extract the product name."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        db_names = ", ".join(article_names) if article_names else "Aucun article"
        
        prompt = (
            "Tu es un assistant logistique. Ta tâche est d'identifier l'article mentionné dans le message WhatsApp.\n"
            "Voici la liste des articles disponibles :\n"
            f"[{db_names}]\n\n"
            "Message WhatsApp : " + text + "\n\n"
            "Règles :\n"
            "1. Identifie l'article le plus proche parmi la liste.\n"
            "2. Retourne uniquement le nom de l'article tel qu'il est dans la liste.\n"
            "3. Si aucun ne correspond de façon convaincante, réponds 'None'.\n"
            "4. Si la demande est vague (ex: 'tournesol' pour 'HUILE DE TOURNESOL'), renvoie le nom complet de l'article."
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
            _logger.error(f"OpenAI Logistics Extraction Error: {str(e)}")
            return None
