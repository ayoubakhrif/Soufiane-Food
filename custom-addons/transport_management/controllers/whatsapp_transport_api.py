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
        exact_driver = request.env['transport.driver'].sudo().search(['|', ('name', '=ilike', message_text.strip()), ('alias_ids.name', '=ilike', message_text.strip())], limit=1)
        
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
            driver_names_list = []
            for d in all_drivers:
                if d.name:
                    aliases = [a.name for a in d.alias_ids if a.name]
                    if aliases:
                        driver_names_list.append(f"{d.name} (Alias: {', '.join(aliases)})")
                    else:
                        driver_names_list.append(d.name)
            
            extracted_name = self._extract_driver_name(message_text, openai_key, driver_names_list)
            
            if not extracted_name or extracted_name.upper() == 'IGNORE':
                _logger.info(f"Ignoring off-topic message in Transport: {group_id}")
                return {'status': 'ignored'}

            if not extracted_name or extracted_name.lower() == 'none':
                return {'status': 'not_found', 'message': "Désolé, je n'ai pas pu identifier le chauffeur dans votre message."}

            # Handle partial match via search
            drivers = request.env['transport.driver'].sudo().search(['|', ('name', 'ilike', extracted_name), ('alias_ids.name', 'ilike', extracted_name)])

        if not drivers:
            return {'status': 'not_found', 'message': f"Aucun chauffeur trouvé pour : '{extracted_name}'."}

        # Check for absolute exact match among multiple results
        if len(drivers) > 1:
            absolute_match = drivers.filtered(lambda d: d.name.lower() == extracted_name.lower() or any(a.name.lower() == extracted_name.lower() for a in d.alias_ids))
            if absolute_match:
                drivers = absolute_match[0]

        if len(drivers) == 1:
            # UNIQUE DRIVER -> GENERATE PDF
            driver = drivers[0]
            
            trips = request.env['transport.trip'].sudo().search([('driver_id', '=', driver.id)])
            remorque_trips = request.env['transport.trip.remorque'].sudo().search([('driver_remorque_id', '=', driver.id)])
            
            total_trips = len(trips) + len(remorque_trips)
            total_price = sum(trips.mapped('total_price')) + sum(remorque_trips.mapped('total_price'))
            total_charges = sum(trips.mapped('total_amount')) + sum(remorque_trips.mapped('total_amount'))
            total_profit = sum(trips.mapped('profit')) + sum(remorque_trips.mapped('profit'))
            
            # Generate HTML Content for PDF
            html_content = self._generate_driver_html(driver, trips, remorque_trips)
            
            report_action = request.env['ir.actions.report'].sudo()
            try:
                pdf_content = report_action._run_wkhtmltopdf([html_content])
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

                summary_msg = f"Voici le rapport pour le chauffeur *{driver.name}*.\n\n"
                summary_msg += f"📊 *Détails* :\n"
                summary_msg += f"• Nom: {driver.name}\n"
                if driver.vehicle_type:
                    summary_msg += f"• Type de véhicule: {driver.vehicle_type}\n"
                summary_msg += f"• Voyages Totaux: {total_trips}\n"
                summary_msg += f"• Chiffre d'Affaires: {'{:,.2f}'.format(total_price).replace(',', ' ')} DH\n"
                summary_msg += f"• Total Charges: {'{:,.2f}'.format(total_charges).replace(',', ' ')} DH\n"
                summary_msg += f"• Bénéfices: {'{:,.2f}'.format(total_profit).replace(',', ' ')} DH\n"
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

    def _generate_driver_html(self, driver, trips, remorque_trips):
        total_trips = len(trips) + len(remorque_trips)
        
        # Totals
        total_price = sum(trips.mapped('total_price')) + sum(remorque_trips.mapped('total_price'))
        total_charges = sum(trips.mapped('total_amount')) + sum(remorque_trips.mapped('total_amount'))
        total_profit = sum(trips.mapped('profit')) + sum(remorque_trips.mapped('profit'))
        
        # Detailed charges
        total_fuel = sum(trips.mapped('charge_fuel')) + sum(remorque_trips.mapped('charge_fuel'))
        total_dep = sum(trips.mapped('charge_driver')) + sum(remorque_trips.mapped('charge_driver'))
        total_adblue = sum(trips.mapped('charge_adblue')) + sum(remorque_trips.mapped('charge_adblue'))
        total_mixed = sum(trips.mapped('charge_mixed')) + sum(remorque_trips.mapped('charge_mixed'))
        
        html = f"""
        <html>
            <head>
                <meta charset="utf-8"/>
                <style>
                    body {{ font-family: sans-serif; font-size: 14px; color: #333; }}
                    h2 {{ text-align: center; color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }}
                    h3 {{ color: #2980b9; margin-top: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 11px; }}
                    th, td {{ border: 1px solid #bdc3c7; padding: 6px 8px; text-align: left; vertical-align: middle; }}
                    th {{ background-color: #ecf0f1; font-weight: bold; color: #2c3e50; }}
                    .info-box {{ background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    .info-box p {{ margin: 5px 0; display: inline-block; width: 48%; }}
                    .stats-box {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
                    .stat-item {{ background-color: #e8f4f8; padding: 15px; border-radius: 5px; flex: 1; margin: 0 5px; text-align: center; border: 1px solid #bce8f1; }}
                    .stat-item:first-child {{ margin-left: 0; }}
                    .stat-item:last-child {{ margin-right: 0; }}
                    .stat-value {{ font-size: 16px; font-weight: bold; color: #31708f; margin-top: 5px; }}
                    .charges-box {{ background-color: #fff3cd; border: 1px solid #ffeeba; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    .charges-box h4 {{ margin-top: 0; color: #856404; margin-bottom: 10px; }}
                    .charges-grid {{ display: flex; flex-wrap: wrap; }}
                    .charge-item {{ width: 25%; margin-bottom: 10px; font-size: 13px; }}
                </style>
            </head>
            <body>
                <h2>Rapport Chauffeur : {driver.name}</h2>
                
                <div class="stats-box">
                    <div class="stat-item">
                        <div>Voyages Totaux</div>
                        <div class="stat-value">{total_trips}</div>
                    </div>
                    <div class="stat-item">
                        <div>Chiffre d'Affaires</div>
                        <div class="stat-value">{'{:,.2f}'.format(total_price).replace(',', ' ')}</div>
                    </div>
                    <div class="stat-item">
                        <div>Charges Totales</div>
                        <div class="stat-value">{'{:,.2f}'.format(total_charges).replace(',', ' ')}</div>
                    </div>
                    <div class="stat-item" style="background-color: #dff0d8; border-color: #d6e9c6;">
                        <div style="color: #3c763d;">Bénéfices Totaux</div>
                        <div class="stat-value" style="color: #3c763d;">{'{:,.2f}'.format(total_profit).replace(',', ' ')}</div>
                    </div>
                </div>

                <div class="charges-box">
                    <h4>Détail des charges :</h4>
                    <div class="charges-grid">
                        <div class="charge-item"><strong>Gazoil :</strong> {'{:,.2f}'.format(total_fuel).replace(',', ' ')} DH</div>
                        <div class="charge-item"><strong>Déplacement :</strong> {'{:,.2f}'.format(total_dep).replace(',', ' ')} DH</div>
                        <div class="charge-item"><strong>AdBlue :</strong> {'{:,.2f}'.format(total_adblue).replace(',', ' ')} DH</div>
                        <div class="charge-item"><strong>Mixe :</strong> {'{:,.2f}'.format(total_mixed).replace(',', ' ')} DH</div>
                    </div>
                </div>

                <div class="info-box">
                    <p><strong>Nom :</strong> {driver.name}</p>
                    <p><strong>Type de véhicule :</strong> {driver.vehicle_type or 'Non spécifié'}</p>
                    <p><strong>Remorque :</strong> {'Oui' if driver.remorque else 'Non'}</p>
                    <p><strong>Salaire Actuel :</strong> {'{:,.2f}'.format(driver.current_monthly_salary).replace(',', ' ')} DH</p>
                </div>
        """
        
        # Add Trips section grouped by month
        all_trips = list(trips) + list(remorque_trips)
        all_trips.sort(key=lambda t: t.date or fields.Date.today(), reverse=True)
        
        if all_trips:
            from collections import defaultdict
            months_fr = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
            trips_by_month = defaultdict(list)
            
            for trip in all_trips:
                if trip.date:
                    month_key = f"{trip.date.year}-{trip.date.month:02d}"
                    month_label = f"{months_fr[trip.date.month - 1]} {trip.date.year}"
                else:
                    month_key = "0000-00"
                    month_label = "Date Inconnue"
                trips_by_month[(month_key, month_label)].append(trip)
            
            # Sort by month descending
            sorted_months = sorted(trips_by_month.keys(), key=lambda x: x[0], reverse=True)
            
            for (month_key, month_label) in sorted_months:
                month_trips = trips_by_month[(month_key, month_label)]
                
                # Month Totals
                m_price = sum(t.total_price for t in month_trips if t.total_price)
                m_charges = sum(t.total_amount for t in month_trips if t.total_amount)
                m_profit = sum(t.profit for t in month_trips if t.profit)
                
                html += f"""
                    <div style="background-color: #2c3e50; color: white; padding: 5px 10px; margin-top: 20px; border-radius: 3px;">
                        <h3 style="margin: 0; color: white;">{month_label} - <em>(CA: {'{:,.2f}'.format(m_price).replace(',', ' ')} DH | Bénéfice: {'{:,.2f}'.format(m_profit).replace(',', ' ')} DH)</em></h3>
                    </div>
                    <table>
                        <tr>
                            <th>Date</th>
                            <th>Client & Dest.</th>
                            <th>Prix (Allée/Retour/Total)</th>
                            <th>Détails des Charges</th>
                            <th>Bénéfice</th>
                            <th>Payé</th>
                        </tr>
                """
                for trip in month_trips:
                    date_str = trip.date.strftime('%d/%m/%Y') if trip.date else ''
                    client = trip.client_id.name if hasattr(trip, 'client_id') and trip.client_id else ''
                    
                    if hasattr(trip, 'destination'):
                        trip_type = dict(trip._fields['destination'].selection or {}).get(trip.destination, trip.destination or '')
                        trip_type += " (Remorque)"
                    else:
                        trip_type = dict(trip._fields['trip_type'].selection or {}).get(trip.trip_type, trip.trip_type or '')
                    
                    p_going = '{:,.2f}'.format(trip.going_price).replace(',', ' ') if trip.going_price else '0.00'
                    p_ret = '{:,.2f}'.format(trip.returning_price).replace(',', ' ') if trip.returning_price else '0.00'
                    p_tot = '{:,.2f}'.format(trip.total_price).replace(',', ' ') if trip.total_price else '0.00'
                    
                    c_fuel = '{:,.2f}'.format(trip.charge_fuel).replace(',', ' ') if trip.charge_fuel else '0.00'
                    c_dep = '{:,.2f}'.format(trip.charge_driver).replace(',', ' ') if trip.charge_driver else '0.00'
                    c_adblue = '{:,.2f}'.format(trip.charge_adblue).replace(',', ' ') if trip.charge_adblue else '0.00'
                    c_mix_val = '{:,.2f}'.format(trip.charge_mixed).replace(',', ' ') if trip.charge_mixed else '0.00'
                    c_mix_note = trip.note if trip.note else ''
                    c_tot = '{:,.2f}'.format(trip.total_amount).replace(',', ' ') if trip.total_amount else '0.00'
                    
                    mix_str = f" | Div: {c_mix_val}"
                    if c_mix_note:
                        mix_str += f" ({c_mix_note})"
                    
                    profit = '{:,.2f}'.format(trip.profit).replace(',', ' ') if trip.profit else '0.00'
                    paid = "Oui" if trip.is_paid else "Non"
                    profit_color = "green" if trip.profit and trip.profit > 0 else ("red" if trip.profit and trip.profit < 0 else "black")
                    
                    html += f"""
                        <tr>
                            <td>{date_str}</td>
                            <td><strong>{client}</strong><br/><span style="color:#7f8c8d; font-size:10px;">{trip_type}</span></td>
                            <td><span style="color:#7f8c8d; font-size:10px;">Allée: {p_going}<br/>Retour: {p_ret}</span><br/><strong>Total: {p_tot}</strong></td>
                            <td style="font-size:10px;">
                                Gaz: {c_fuel} | Dép: {c_dep} | AdB: {c_adblue}{mix_str}<br/>
                                <strong>Total: {c_tot}</strong>
                            </td>
                            <td style="color: {profit_color}; font-weight: bold;">{profit}</td>
                            <td>{paid}</td>
                        </tr>
                    """
                html += "</table>"
            
        html += """
            </body>
        </html>
        """
        return html
