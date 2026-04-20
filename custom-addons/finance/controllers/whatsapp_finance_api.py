import base64
import json
import logging
import requests
from odoo import http, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppFinanceController(http.Controller):

    @http.route('/api/whatsapp/finance', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_finance_report(self, **kwargs):
        # Force database
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        # 1. Verification of API Key
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'whatsapp_direct_quantity')
        
        if not api_key or api_key != expected_api_key:
            _logger.warning("Unauthorized access attempt to WhatsApp Finance API")
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

        # 3. Security: Check Group ID
        FINANCE_GROUP_ID = '120363428965532100@g.us'
        if group_id != FINANCE_GROUP_ID:
            _logger.info(f"Ignoring request from group {group_id} in Finance Agent")
            return {'status': 'ignored', 'message': 'This agent only handles the Finance Group.'}

        # 4. Handle Exact Match First
        exact_benif = request.env['finance.benif'].sudo().search([('name', '=ilike', message_text)], limit=1)
        
        if exact_benif:
            benifs = exact_benif
            extracted_name = exact_benif.name
        else:
            # 5. Call OpenAI to extract beneficiary name
            openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
            if not openai_key:
                return {'status': 'error', 'message': 'OpenAI API key not configured'}

            # Fetch all beneficiary names
            all_benifs = request.env['finance.benif'].sudo().search([])
            benif_names_list = [b.name for b in all_benifs if b.name]
            
            extracted_name = self._extract_benif_name(message_text, openai_key, benif_names_list)
            
            if not extracted_name or extracted_name.lower() == 'none':
                return {'status': 'not_found', 'message': "Désolé, je n'ai pas pu identifier le bénéficiaire dans votre message."}

            # Handle partial match via search
            benifs = request.env['finance.benif'].sudo().search([('name', 'ilike', extracted_name)])

        if not benifs:
            return {'status': 'not_found', 'message': f"Aucun bénéficiaire trouvé pour : '{extracted_name}'."}

        # Check for absolute exact match among multiple results
        if len(benifs) > 1:
            absolute_match = benifs.filtered(lambda b: b.name.lower() == extracted_name.lower())
            if absolute_match:
                benifs = absolute_match[0]

        if len(benifs) == 1:
            # UNIQUE BENEFICIARY -> GENERATE PDF
            benif = benifs[0]
            report_action = request.env['ir.actions.report'].sudo()
            pdf_content, _ = report_action._render_qweb_pdf('finance.action_report_finance_benif_summary', res_ids=benif.ids)
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            stats = benif.get_cheque_stats()
            summary_msg = f"Voici le rapport financier pour *{benif.name}*.\n\n"
            summary_msg += f"📊 *Analyse des Chèques* :\n"
            summary_msg += f"• Total: {stats['total']}\n"
            summary_msg += f"• Encaissés: {stats['encaisse']}\n"
            summary_msg += f"• Restants: {stats['non_encaisse']}\n\n"
            summary_msg += f"💰 Solde: *{'{:,.2f}'.format(benif.solde).replace(',', ' ')} DH*"

            from odoo import fields
            return {
                'status': 'success',
                'product_name': benif.name,
                'message': summary_msg,
                'pdf_base64': pdf_base64,
                'file_name': f"Rapport_Finance_{benif.name.replace(' ', '_')}_{fields.Date.today()}.pdf"
            }
            
        else:
            # MULTIPLE BENEFICIARIES FOUND
            choices = [b.name for b in benifs]
            choices_text = "Plusieurs bénéficiaires correspondent. Veuillez préciser :\n"
            for i, name in enumerate(choices, 1):
                choices_text += f"{i}- {name}\n"
                
            return {
                'status': 'multiple_choices',
                'message': choices_text,
                'choices': choices
            }

    def _extract_benif_name(self, text, api_key, names_list):
        """Use OpenAI to extract the beneficiary name."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        db_names = ", ".join(names_list) if names_list else "Aucun bénéficiaire disponible"
        
        prompt = (
            "Tu es un assistant comptable. Ta tâche est d'identifier le nom du bénéficiaire (fournisseur) mentionné dans un message WhatsApp.\n"
            "Voici la liste des bénéficiaires de la base de données :\n"
            f"[{db_names}]\n\n"
            "Message WhatsApp : " + text + "\n\n"
            "Règles :\n"
            "1. Identifie le nom le plus proche dans la liste.\n"
            "2. Retourne uniquement le nom du bénéficiaire.\n"
            "3. Si aucun ne correspond, réponds 'None'.\n"
            "Retourne UNIQUEMENT le résultat."
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
            _logger.error(f"OpenAI Finance Extraction Error: {str(e)}")
            return None
