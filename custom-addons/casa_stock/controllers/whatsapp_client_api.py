import base64
import json
import logging
import requests
from odoo import http, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppClientController(http.Controller):

    @http.route('/api/whatsapp/client', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_client_report(self, **kwargs):
        # En mode auth='none', on force la base de données
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        # 1. Verification of API Key
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        # Use the same key as the other agent or a dedicated one
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'default-secret-key')
        
        if not api_key or api_key != expected_api_key:
            _logger.warning("Unauthorized access attempt to WhatsApp Client API")
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

        # --- NEW: Check for Global Client Report trigger ---
        client_total_triggers = ['client total', 'total client', 'solde total', 'situation globale', 'situation generale']
        if any(trigger in message_text.lower() for trigger in client_total_triggers):
            report_action = request.env.ref('casa_stock.action_report_casa_clients_total').sudo()
            # Use current date via odoo.fields
            from odoo import fields
            
            # The report method searches all clients with balance != 0
            dummy_record = request.env['casa.client'].sudo().search([('compte_total', '!=', 0)], limit=1)
            if not dummy_record:
                return {'status': 'not_found', 'message': "Désolé, il n'y a actuellement aucun solde client à afficher."}
            
            pdf_content, _ = report_action._render_qweb_pdf(report_action.id, res_ids=dummy_record.ids)
            
            return {
                'status': 'success',
                'message': "Voici la situation globale des comptes clients.",
                'pdf_base64': base64.b64encode(pdf_content).decode('utf-8'),
                'file_name': f"Situation_Globale_Clients_{fields.Date.today()}.pdf"
            }
        # ----------------------------------------------------

        # 3. Security: Check Group ID
        # Only handle requests from the Director's Client Group
        DIRECTOR_GROUP_ID = '120363426234155722@g.us'
        if group_id != DIRECTOR_GROUP_ID:
            _logger.info(f"Ignoring request from group {group_id} in Client Agent")
            return {'status': 'ignored', 'message': 'This agent only handles the Client Account Group.'}

        # 4. Handle Exact Match First (Bypass OpenAI for menu selections)
        exact_client = request.env['casa.client'].sudo().search([('name', '=ilike', message_text)], limit=1)
        
        if exact_client:
            clients = exact_client
            extracted_name = exact_client.name
        else:
            # 5. Call OpenAI to extract client name
            openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
            if not openai_key:
                return {'status': 'error', 'message': 'OpenAI API key not configured in Odoo (parameter: whatsapp_stock.openai_key)'}

            # Fetch all client names to guide the AI
            all_clients = request.env['casa.client'].sudo().search([])
            client_names_list = [c.name for c in all_clients if c.name]
            
            extracted_name = self._extract_client_name(message_text, openai_key, client_names_list)
            
            if not extracted_name or extracted_name.lower() == 'none':
                return {'status': 'not_found', 'message': "Désolé, je n'ai pas pu identifier le client dans votre message."}

            # Handle partial match via search
            clients = request.env['casa.client'].sudo().search([('name', 'ilike', extracted_name)])

        if not clients:
            return {'status': 'not_found', 'message': f"Aucun client trouvé pour : '{extracted_name}'."}

        # Check for absolute exact match among multiple results to break loops
        if len(clients) > 1:
            absolute_match = clients.filtered(lambda c: c.name.lower() == extracted_name.lower())
            if absolute_match:
                clients = absolute_match[0]

        if len(clients) == 1:
            # UNIQUE CLIENT -> GENERATE PDF (ALL WEEKS)
            client = clients[0]
            report_action = request.env['ir.actions.report'].sudo()
            pdf_content, _ = report_action._render_qweb_pdf('casa_stock.action_report_casa_client_history', res_ids=client.ids)
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            return {
                'status': 'success',
                'client_name': client.name,
                'pdf_base64': pdf_base64,
                'file_name': f"Rapport_Compte_{client.name.replace(' ', '_')}.pdf"
            }
            
        else:
            # MULTIPLE CLIENTS FOUND
            choices = [c.name for c in clients]
            choices_text = "Plusieurs clients correspondent à votre demande. Veuillez préciser :\n"
            for i, name in enumerate(choices, 1):
                choices_text += f"{i}- {name}\n"
                
            return {
                'status': 'multiple_choices',
                'message': choices_text,
                'choices': choices
            }

    def _extract_client_name(self, text, api_key, client_names_list):
        """Use OpenAI to extract the client name from a natural language sentence."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        db_names = ", ".join(client_names_list) if client_names_list else "Aucun client disponible"
        
        prompt = (
            "Tu es un assistant administratif. Ta tâche est d'identifier le nom correct du client demandé pour un rapport de compte.\n"
            "Voici la liste des clients de la base de données :\n"
            f"[{db_names}]\n\n"
            "Message WhatsApp : " + text + "\n\n"
            "Règles strictes :\n"
            "1. Identifie le nom du client mentionné.\n"
            "2. Retourne le nom du client tel qu'il apparaît dans la liste (le plus proche possible).\n"
            "3. IMPORTANT : Si la demande est globale ou partielle (ex: 'taggada') et que plusieurs clients de la liste correspondent, renvoie UNIQUEMENT le terme commun (ex: 'taggada'). Ne choisis pas un client au hasard si la demande est vague !\n"
            "4. Si aucun client ne correspond du tout, réponds 'None'.\n"
            "Retourne UNIQUEMENT le texte identifié (sans guillemets, sans rien de plus)."
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
            _logger.error(f"OpenAI Client Extraction Error: {str(e)}")
            return None
