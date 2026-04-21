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

        # 4. Search for Article (Check both Logistique and Achat articles)
        # Search using ilike first to be flexible
        search_domain = [('name', 'ilike', message_text)]
        log_articles = request.env['logistique.article'].sudo().search(search_domain)
        achat_articles = request.env['achat.article'].sudo().search(search_domain)
        
        # Build initial items
        found_items = []
        for a in log_articles:
            found_items.append({'name': a.name, 'model': 'logistique.article', 'id': a.id, 'company_id': a.company_article_id.id})
        for a in achat_articles:
            found_items.append({'name': a.name, 'model': 'achat.article', 'id': a.id, 'company_id': a.company_article_id.id})

        # 4.1 CASE-SENSITIVE EXACT MATCH (Break loops)
        # If the input matches exactly one article name (case sensitive), we prioritize it to prevent loops
        case_exact = [f for f in found_items if f['name'] == message_text]
        if len(case_exact) == 1:
            selected_item = case_exact[0]
        else:
            # B. AI Fallback if no result or many results (to clarify)
            if not found_items:
                openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
                if openai_key:
                    all_names = list(set(
                        request.env['logistique.article'].sudo().search([]).mapped('name') + 
                        request.env['achat.article'].sudo().search([]).mapped('name')
                    ))
                    extracted_name = self._extract_product_name(message_text, openai_key, all_names)
                    if extracted_name and extracted_name.lower() != 'none':
                        log_articles = request.env['logistique.article'].sudo().search([('name', 'ilike', extracted_name)])
                        achat_articles = request.env['achat.article'].sudo().search([('name', 'ilike', extracted_name)])
                        for a in log_articles:
                            found_items.append({'name': a.name, 'model': 'logistique.article', 'id': a.id, 'company_id': a.company_article_id.id})
                        for a in achat_articles:
                            found_items.append({'name': a.name, 'model': 'achat.article', 'id': a.id, 'company_id': a.company_article_id.id})

            if not found_items:
                return {'status': 'not_found', 'message': f"Désolé, je n'ai pas trouvé l'article '{message_text}' dans la logistique."}

            # 5. Handle Multiple Choices
            if len(found_items) > 1:
                # Group by case-insensitive name first
                unique_names = {}
                for f in found_items:
                    lname = f['name'].lower()
                    if lname not in unique_names:
                        unique_names[lname] = f
                
                if len(unique_names) > 1:
                    choices = [f['name'] for f in unique_names.values()]
                    choices_text = "Plusieurs articles correspondent à votre demande. Veuillez préciser :\n"
                    for i, name in enumerate(choices, 1):
                        choices_text += f"{i}- {name}\n"
                    return {
                        'status': 'multiple_choices',
                        'message': choices_text,
                        'choices': choices
                    }
                else:
                    # They all have the same name (case-insensitive)
                    selected_item = list(unique_names.values())[0]
            else:
                selected_item = found_items[0]

        # 6. Process Selection
        target_name = selected_item['name']
        company_id = selected_item['company_id']
        
        # Find all logistique and achat articles sharing the same company ID or same name
        all_log_ids = []
        all_achat_ids = []
        
        if company_id:
            all_log_ids = request.env['logistique.article'].sudo().search([('company_article_id', '=', company_id)]).ids
            all_achat_ids = request.env['achat.article'].sudo().search([('company_article_id', '=', company_id)]).ids
        else:
            # Fallback to name if no company link
            all_log_ids = request.env['logistique.article'].sudo().search([('name', '=', target_name)]).ids
            all_achat_ids = request.env['achat.article'].sudo().search([('name', '=', target_name)]).ids

        # Final Search in logistique.entry
        domain = [
            '|', '|',
            ('achat_article_id', 'in', all_achat_ids),
            ('article_id', 'in', all_log_ids),
            ('achat_article_id.name', 'ilike', target_name)
        ]
        entries = request.env['logistique.entry'].sudo().search(domain, order='eta asc')

        if not entries:
            return {
                'status': 'response',
                'response': f"📋 *Logistique : {target_name}*\n\n✅ Aucun dossier trouvé en base pour cet article."
            }

        # 7. Group entries
        today = fields.Date.today()
        at_port = []
        upcoming = {}
        exited_count = 0

        for entry in entries:
            # We filter by port_status here to show more info if nothing matches
            if entry.port_status == 'exited':
                exited_count += 1
                continue
            
            cnt = entry.container_count or 0
            # Use entry ETA, fallback to dossier ETA if needed
            eta_val = entry.eta or (entry.dossier_id and entry.dossier_id.eta) or False
            
            if eta_val and eta_val < today:
                at_port.append({
                    'bl': entry.bl_number or 'Inconnu',
                    'count': cnt,
                    'eta': eta_val.strftime('%d/%m/%Y')
                })
            else:
                eta_str = eta_val.strftime('%d/%m/%Y') if eta_val else "Date inconnue/À venir"
                upcoming[eta_str] = upcoming.get(eta_str, 0) + cnt

        # 8. Format Response
        response = f"🚢 *LOGISTIQUE - {article.name.upper()}*\n"
        response += f"━━━━━━━━━━━━━━━━━━\n\n"

        if not at_port and not upcoming:
            response += f"✅ Dossiers trouvés ({exited_count}), mais ils sont tous déjà sortis (Status: Exited).\n"
            return {'status': 'response', 'response': response}

        # Section: At Port
        if at_port:
            total_at_port = sum(item['count'] for item in at_port)
            response += f"⚓ *DÉJÀ SUR PORT ({total_at_port} conteneurs)*\n"
            for item in at_port:
                response += f"• BL {item['bl']} : *{item['count']}* cont. (ETA: {item['eta']})\n"
            response += "\n"

        # Section: Upcoming
        if upcoming:
            # Sort upcoming by date (handle 'Date inconnue' gracefully)
            response += f"📅 *ARRIVAGES À VENIR*\n"
            for eta_date in sorted(upcoming.keys()):
                response += f"• Le *{eta_date}* : *{upcoming[eta_date]}* conteneurs\n"

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
