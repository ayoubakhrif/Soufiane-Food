import base64
import json
import logging
import requests
from odoo import http, SUPERUSER_ID, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppTransportController(http.Controller):

    @http.route('/api/whatsapp/transport', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_transport_report(self, **kwargs):
        # Force database
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        # 1. Verification of API Key
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'whatsapp_direct_quantity')
        
        if not api_key or api_key != expected_api_key:
            _logger.warning("Unauthorized access attempt to WhatsApp Transport API")
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
        TRANSPORT_GROUP_ID = '120363409412071351@g.us'
        if group_id != TRANSPORT_GROUP_ID:
            _logger.info(f"Ignoring request from group {group_id} in Transport Agent")
            return {'status': 'ignored', 'message': 'This agent only handles the Transport Group.'}

        # 4. Check for direct match first
        exact_driver = request.env['transport.driver'].sudo().search([('name', '=ilike', message_text.strip())], limit=1)
        
        if exact_driver:
            drivers = exact_driver
            extracted_name = exact_driver.name
        else:
            # 5. Call OpenAI to extract driver name
            openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
            if not openai_key:
                return {'status': 'error', 'message': 'OpenAI API key not configured'}

            # Fetch all driver names
            all_drivers = request.env['transport.driver'].sudo().search([])
            driver_names_list = [d.name for d in all_drivers if d.name]
            
            extracted_name = self._extract_driver_name(message_text, openai_key, driver_names_list)
            
            if not extracted_name or extracted_name.upper() == 'IGNORE':
                _logger.info(f"Ignoring off-topic message in Transport: {group_id}")
                return {'status': 'ignored'}

            if not extracted_name or extracted_name.lower() == 'none':
                return {'status': 'not_found', 'message': "Désolé, je n'ai pas pu identifier le chauffeur dans votre message."}

            # Handle partial match via search
            drivers = request.env['transport.driver'].sudo().search([('name', 'ilike', extracted_name)])

        if not drivers:
            return {'status': 'not_found', 'message': f"Aucun chauffeur trouvé pour : '{extracted_name}'."}

        # Check for absolute exact match among multiple results
        if len(drivers) > 1:
            absolute_match = drivers.filtered(lambda d: d.name.lower() == extracted_name.lower())
            if absolute_match:
                drivers = absolute_match[0]

        if len(drivers) == 1:
            # UNIQUE DRIVER -> GENERATE PDF
            driver = drivers[0]
            
            # Generate HTML Content for PDF
            html_content = self._generate_driver_html(driver)
            
            report_action = request.env['ir.actions.report'].sudo()
            try:
                pdf_content = report_action._run_wkhtmltopdf([html_content])
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

                summary_msg = f"Voici le rapport pour le chauffeur *{driver.name}*.\n\n"
                summary_msg += f"📊 *Détails* :\n"
                summary_msg += f"• Nom: {driver.name}\n"
                summary_msg += f"• Remorque: {'Oui' if driver.remorque else 'Non'}\n"
                summary_msg += f"• Salaire Actuel: {'{:,.2f}'.format(driver.current_monthly_salary).replace(',', ' ')} DH\n"

                return {
                    'status': 'success',
                    'product_name': driver.name,
                    'message': summary_msg,
                    'pdf_base64': pdf_base64,
                    'file_name': f"Rapport_Chauffeur_{driver.name.replace(' ', '_')}_{fields.Date.today()}.pdf"
                }
            except Exception as e:
                _logger.error(f"Error generating PDF for Transport Driver: {str(e)}")
                return {'status': 'error', 'message': f"Erreur lors de la génération du rapport PDF : {str(e)}"}
            
        else:
            # MULTIPLE DRIVERS FOUND
            choices = [d.name for d in drivers]
            choices_text = "Plusieurs chauffeurs correspondent. Veuillez préciser :\n"
            for i, name in enumerate(choices, 1):
                choices_text += f"{i}- {name}\n"
                
            return {
                'status': 'multiple_choices',
                'message': choices_text,
                'choices': choices
            }

    def _extract_driver_name(self, text, api_key, names_list):
        """Use OpenAI to extract the driver name."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        db_names = ", ".join(names_list) if names_list else "Aucun chauffeur disponible"
        
        prompt = (
            "Tu es un assistant logistique. Ta tâche est d'identifier le nom du chauffeur mentionné dans un message WhatsApp.\n"
            "Voici la liste des chauffeurs de la base de données :\n"
            f"[{db_names}]\n\n"
            "Message WhatsApp : " + text + "\n\n"
            "Règles :\n"
            "1. Identifie le nom le plus proche dans la liste.\n"
            "2. Retourne uniquement le nom du chauffeur.\n"
            "3. IMPORTANT : Si le message ne contient QUE des emojis ou ne contient QUE des caractères aléatoires sans sens, réponds UNIQUEMENT 'IGNORE'.\n"
            "4. Pour tout autre message, tente d'identifier le chauffeur ou réponds 'None' si aucun ne correspond.\n"
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
            _logger.error(f"OpenAI Transport Extraction Error: {str(e)}")
            return None

    def _generate_driver_html(self, driver):
        html = f"""
        <html>
            <head>
                <meta charset="utf-8"/>
                <style>
                    body {{ font-family: sans-serif; font-size: 14px; color: #333; }}
                    h2 {{ text-align: center; color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }}
                    h3 {{ color: #2980b9; margin-top: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 13px; }}
                    th, td {{ border: 1px solid #bdc3c7; padding: 8px 10px; text-align: left; vertical-align: middle; }}
                    th {{ background-color: #ecf0f1; font-weight: bold; color: #2c3e50; }}
                    .info-box {{ background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    .info-box p {{ margin: 5px 0; }}
                </style>
            </head>
            <body>
                <h2>Rapport Chauffeur : {driver.name}</h2>
                <div class="info-box">
                    <p><strong>Nom :</strong> {driver.name}</p>
                    <p><strong>Remorque :</strong> {'Oui' if driver.remorque else 'Non'}</p>
                    <p><strong>Salaire Actuel :</strong> {'{:,.2f}'.format(driver.current_monthly_salary).replace(',', ' ')} DH</p>
                </div>
        """
        
        # Add Avances section
        if driver.advance_ids:
            html += """
                <h3>Dernières Avances</h3>
                <table>
                    <tr>
                        <th>Date</th>
                        <th>Montant (DH)</th>
                        <th>Description</th>
                        <th>État</th>
                    </tr>
            """
            for advance in driver.advance_ids.sorted(key=lambda a: a.create_date, reverse=True)[:10]:
                date_str = advance.date.strftime('%d/%m/%Y') if hasattr(advance, 'date') and advance.date else ''
                amount = '{:,.2f}'.format(advance.amount).replace(',', ' ') if hasattr(advance, 'amount') else '0.00'
                desc = advance.name if hasattr(advance, 'name') else ''
                state = advance.state if hasattr(advance, 'state') else ''
                
                html += f"""
                    <tr>
                        <td>{date_str}</td>
                        <td>{amount}</td>
                        <td>{desc}</td>
                        <td>{state}</td>
                    </tr>
                """
            html += "</table>"
            
        html += """
            </body>
        </html>
        """
        return html
