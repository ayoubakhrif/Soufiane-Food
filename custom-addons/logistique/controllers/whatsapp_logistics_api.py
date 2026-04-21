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

        # 4. Search for Article (Filter by Active Dossiers Only)
        active_entries = request.env['logistique.entry'].sudo().search([
            ('port_status', '=', 'on_port')
        ])
        active_log_ids = active_entries.mapped('article_id').ids
        active_achat_ids = active_entries.mapped('achat_article_id').ids
        
        # Search Logistique Articles by Name OR Alias (via company_article_id)
        log_articles = request.env['logistique.article'].sudo().search([
            '|', ('name', 'ilike', message_text), ('company_article_id.alias_ids.name', 'ilike', message_text),
            ('id', 'in', active_log_ids)
        ])
        
        # Search Achat Articles by Name OR Alias (via company_article_id)
        achat_articles = request.env['achat.article'].sudo().search([
            '|', ('name', 'ilike', message_text), ('company_article_id.alias_ids.name', 'ilike', message_text),
            ('id', 'in', active_achat_ids)
        ])
        
        # Build initial items
        found_items = []
        for a in log_articles:
            found_items.append({'name': a.name, 'model': 'logistique.article', 'id': a.id, 'company_id': a.company_article_id.id})
        for a in achat_articles:
            found_items.append({'name': a.name, 'model': 'achat.article', 'id': a.id, 'company_id': a.company_article_id.id})

        # 4.1 CASE-SENSITIVE EXACT MATCH (Break loops)
        case_exact = [f for f in found_items if f['name'] == message_text]
        if len(case_exact) == 1:
            selected_item = case_exact[0]
        else:
            # B. AI Fallback (Active Articles Only)
            if not found_items:
                openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
                if openai_key:
                    active_log_recs = request.env['logistique.article'].sudo().browse(active_log_ids)
                    active_achat_recs = request.env['achat.article'].sudo().browse(active_achat_ids)
                    
                    active_names = list(set(active_log_recs.mapped('name') + active_achat_recs.mapped('name')))
                    active_names = [name for name in active_names if name]
                    
                    if active_names:
                        extracted_name = self._extract_product_name(message_text, openai_key, active_names)
                        
                        if not extracted_name or extracted_name.upper() == 'IGNORE':
                            _logger.info(f"Ignoring off-topic message in Logistics: {group_id}")
                            return {'status': 'ignored'}
                        
                        if extracted_name and extracted_name.lower() != 'none':
                            # Limit AI match to ACTIVE articles as well
                            log_articles = request.env['logistique.article'].sudo().search([
                                '|', ('name', '=', extracted_name), ('company_article_id.alias_ids.name', '=', extracted_name),
                                ('id', 'in', active_log_ids)
                            ])
                            achat_articles = request.env['achat.article'].sudo().search([
                                '|', ('name', '=', extracted_name), ('company_article_id.alias_ids.name', '=', extracted_name),
                                ('id', 'in', active_achat_ids)
                            ])
                            for a in log_articles:
                                found_items.append({'name': a.name, 'model': 'logistique.article', 'id': a.id, 'company_id': a.company_article_id.id})
                            for a in achat_articles:
                                found_items.append({'name': a.name, 'model': 'achat.article', 'id': a.id, 'company_id': a.company_article_id.id})

            # C. DISTINGUISH ERROR CASES: If still no result, check if article exists at all
            if not found_items:
                # Search in ALL articles (excluding active status)
                all_log = request.env['logistique.article'].sudo().search([
                    '|', ('name', 'ilike', message_text), ('company_article_id.alias_ids.name', 'ilike', message_text)
                ], limit=1)
                all_achat = request.env['achat.article'].sudo().search([
                    '|', ('name', 'ilike', message_text), ('company_article_id.alias_ids.name', 'ilike', message_text)
                ], limit=1)
                
                if all_log or all_achat:
                    # Article exists but has no active dossiers
                    art_name = all_log[0].name if all_log else all_achat[0].name
                    return {
                        'status': 'response',
                        'response': f"📋 *Logistique : {art_name.upper()}*\n\n✅ Cet article n'a aucun dossier actuellement 'Sur Port' ou à venir."
                    }
                
                # Check with AI in ALL articles for typo handling
                openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
                if openai_key:
                    # FETCH ALL NAMES INCLUDING ALIASES FOR AI GUIDANCE
                    all_article_names = list(set(
                        request.env['logistique.article'].sudo().search([]).mapped('name') + 
                        request.env['achat.article'].sudo().search([]).mapped('name') +
                        request.env['company.article.alias'].sudo().search([]).mapped('name')
                    ))
                    extracted_name = self._extract_product_name(message_text, openai_key, all_article_names)
                    
                    if not extracted_name or extracted_name.upper() == 'IGNORE':
                        _logger.info(f"Ignoring off-topic message in Logistics (Global check): {group_id}")
                        return {'status': 'ignored'}

                    if extracted_name and extracted_name.lower() != 'none':
                        # Check if matches article name or company alias
                        matched_achat = request.env['achat.article'].sudo().search([
                            '|', ('name', '=', extracted_name), ('company_article_id.alias_ids.name', '=', extracted_name)
                        ], limit=1)
                        matched_name = matched_achat.name if matched_achat else extracted_name
                        
                        return {
                            'status': 'response',
                            'response': f"📋 *Logistique : {matched_name.upper()}*\n\n✅ Cet article existe mais n'a aucun dossier 'Sur Port' actuellement."
                        }

                return {'status': 'not_found', 'message': f"❌ Désolé, l'article '{message_text}' n'est pas reconnu par le système."}

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
        response = f"🚢 *LOGISTIQUE - {target_name.upper()}*\n"
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
            "3. IMPORTANT : Si le message ne contient QUE des emojis (ex: '🚀🚀') ou ne contient QUE des caractères aléatoires sans sens (ex: 'qsdqsd', '...', '???'), réponds UNIQUEMENT 'IGNORE'.\n"
            "4. Pour tout autre message (salutations, fautes de frappe, phrases complètes), tente d'identifier l'article ou réponds 'None' si aucun ne correspond.\n"
            "5. Si la demande est vague (ex: 'tournesol' pour 'HUILE DE TOURNESOL'), renvoie le nom complet de l'article.\n"
            "Retourne UNIQUEMENT le résultat (ou IGNORE)."
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
