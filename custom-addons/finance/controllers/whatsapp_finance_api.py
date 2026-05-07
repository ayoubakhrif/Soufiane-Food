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

        # 3.1 Handle Documentation Interactive Choices
        if False: # message_text.startswith("DOC_OUI_"):
            try:
                phys_id = int(message_text[8:])
                physical = request.env['finance.cheque.physical'].sudo().browse(phys_id)
                if physical.exists():
                    choices = [
                        f"DOC_LINK_VIDE_{physical.id}",
                        f"DOC_LINK_DOC_{physical.id}",
                        f"DOC_LINK_CHQ_{physical.id}"
                    ]
                    choices_text = (
                        f"Voici les documents disponibles pour le chèque *#{physical.name}* :\n"
                        f"1- Chèque vide\n"
                        f"2- Documentation\n"
                        f"3- Chèque\n\n"
                        f"Veuillez choisir le numéro du document que vous souhaitez ouvrir."
                    )
                    return {
                        'status': 'multiple_choices',
                        'message': choices_text,
                        'choices': choices
                    }
            except Exception as e:
                _logger.error(f"Error handling DOC_OUI_ choice: {str(e)}")

        if False: # message_text.startswith("DOC_NON_"):
            return {
                'status': 'success',
                'response': "D'accord, je reste à votre disposition si vous avez d'autres demandes ! 😊"
            }

        if False: # message_text.startswith("DOC_LINK_"):
            try:
                pdf_data = None
                file_name = ""
                name = ""
                if message_text.startswith("DOC_LINK_VIDE_"):
                    phys_id = int(message_text[14:])
                    physical = request.env['finance.cheque.physical'].sudo().browse(phys_id)
                    pdf_data = physical.chq_vide_pdf
                    file_name = physical.chq_vide_filename or f"Cheque_Vide_{physical.name}.pdf"
                    name = "Chèque vide"
                elif message_text.startswith("DOC_LINK_DOC_"):
                    phys_id = int(message_text[13:])
                    physical = request.env['finance.cheque.physical'].sudo().browse(phys_id)
                    pdf_data = physical.doc_pdf
                    file_name = physical.doc_filename or f"Documentation_{physical.name}.pdf"
                    name = "Documentation"
                elif message_text.startswith("DOC_LINK_CHQ_"):
                    phys_id = int(message_text[13:])
                    physical = request.env['finance.cheque.physical'].sudo().browse(phys_id)
                    pdf_data = physical.cheque_copy_pdf
                    file_name = physical.cheque_copy_filename or f"Cheque_{physical.name}.pdf"
                    name = "Chèque"
                
                if pdf_data:
                    # Odoo binaries are already base64-encoded bytes or string
                    pdf_base64 = pdf_data.decode('utf-8') if isinstance(pdf_data, bytes) else pdf_data
                    return {
                        'status': 'success',
                        'product_name': f"{name} du chèque #{physical.name}",
                        'pdf_base64': pdf_base64,
                        'file_name': file_name
                    }
                else:
                    return {
                        'status': 'success',
                        'response': f"Désolé, le fichier pour *{name}* de ce chèque n'a pas été uploadé dans Odoo."
                    }
            except Exception as e:
                _logger.error(f"Error handling DOC_LINK_ choice: {str(e)}")



        # 4. Handle Talon Logic
        if message_text.lower().startswith("talon"):

            company_part = message_text[5:].strip()
            if company_part:
                # Search for company
                ste = request.env['finance.ste'].sudo().search([('name', 'ilike', company_part)], limit=1)
                if ste:
                    talons = request.env['finance.talon'].sudo().search([('ste_id', '=', ste.id)])
                    if talons:
                        choices = [t.name_shown for t in talons]
                        choices_text = f"Voici les talons pour *{ste.name}* :\n"
                        for i, t in enumerate(talons, 1):
                            # Get human readable state
                            state_label = dict(t._fields['etat'].selection).get(t.etat, t.etat)
                            choices_text += f"{i}- {t.name_shown} ({state_label})\n"
                        
                        return {
                            'status': 'multiple_choices',
                            'message': choices_text,
                            'choices': choices
                        }
                    else:
                        return {'status': 'not_found', 'message': f"Aucun talon trouvé pour la société '{ste.name}'."}
                else:
                    return {'status': 'not_found', 'message': f"Société '{company_part}' non trouvée."}

        # 5. Handle Cheque Number Search
        import re
        is_cheque_search = False
        cheque_number = None
        
        # A. Check if 7 digits numeric (Direct Search)
        if message_text.isdigit() and len(message_text) == 7:
            is_cheque_search = True
            cheque_number = message_text
        
        # B. Check if it's a choice result like "CHQ 2102572 (Company A)"
        match = re.match(r"CHQ (\d{7}) \((.+)\)", message_text)
        if match:
            is_cheque_search = True
            cheque_number = match.group(1)
            company_name = match.group(2)
            # Find specific physical cheque
            cheque = request.env['finance.cheque.physical'].sudo().search([
                ('name', '=', cheque_number),
                ('ste_id.name', '=', company_name)
            ], limit=1)
            if cheque:
                return self._format_physical_cheque_details(cheque)

        if is_cheque_search:
            # Search for PHYSICAL cheques (groups by company)
            cheques = request.env['finance.cheque.physical'].sudo().search([('name', '=', cheque_number)])
            if cheques:
                if len(cheques) == 1:
                    return self._format_physical_cheque_details(cheques[0])
                else:
                    choices = [f"CHQ {c.name} ({c.ste_id.name})" for c in cheques]
                    choices_text = f"Le chèque *{cheque_number}* existe pour plusieurs sociétés. Veuillez choisir :\n"
                    for i, choice in enumerate(choices, 1):
                        choices_text += f"{i}- {choice}\n"
                    
                    return {
                        'status': 'multiple_choices',
                        'message': choices_text,
                        'choices': choices
                    }

        # 6. Handle Exact Matches (Talon Name or Beneficiary Name)
        exact_talon = request.env['finance.talon'].sudo().search([('name_shown', '=ilike', message_text)], limit=1)
        if exact_talon:
            talon = exact_talon[0]
            report_action = request.env['ir.actions.report'].sudo()
            pdf_content, _ = report_action._render_qweb_pdf('finance.action_report_finance_talon_summary', res_ids=talon.ids)
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            stats = talon.get_talon_stats()
            summary_msg = f"Voici les détails du talon *{talon.name_shown}* ({talon.ste_id.name}).\n\n"
            summary_msg += f"📊 *Statistiques* :\n"
            summary_msg += f"• Total: {stats['total']}\n"
            summary_msg += f"• Utilisés: {stats['used']}\n"
            summary_msg += f"• Restants: {stats['remaining']}\n"
            summary_msg += f"• État: *{stats['etat']}*"

            from odoo import fields
            return {
                'status': 'success',
                'product_name': talon.name_shown,
                'message': summary_msg,
                'pdf_base64': pdf_base64,
                'file_name': f"Talon_{talon.name_shown.replace(' ', '_')}_{fields.Date.today()}.pdf"
            }

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
            
            if not extracted_name or extracted_name.upper() == 'IGNORE':
                _logger.info(f"Ignoring off-topic message in Finance: {group_id}")
                return {'status': 'ignored'}

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
            "3. IMPORTANT : Si le message ne contient QUE des emojis (ex: '🚀🚀') ou ne contient QUE des caractères aléatoires sans sens (ex: 'qsdqsd', '...', '???'), réponds UNIQUEMENT 'IGNORE'.\n"
            "4. Pour tout autre message (salutations, fautes de frappe, phrases complètes), tente d'identifier le bénéficiaire ou réponds 'None' si aucun ne correspond.\n"
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
            _logger.error(f"OpenAI Finance Extraction Error: {str(e)}")
            return None

    def _format_physical_cheque_details(self, physical):
        # Force re-read to ensure we have latest computed status
        physical = physical.sudo().with_context(bin_size=True).browse(physical.id)
        
        # Determine global status
        is_encaissé = physical.encours == 'encaisse' or any(d.date_encaissement for d in physical.datacheque_ids)
        status_label = "Encaissé" if is_encaissé else "En cours"
        
        msg = f"📄 *Détails du Chèque Physique #{physical.name}*\n\n"
        msg += f"🏢 *Société:* {physical.ste_id.name}\n"
        msg += f"💰 *Montant Total:* {'{:,.2f}'.format(physical.amount_total).replace(',', ' ')} DH\n"
        msg += f"📅 *Émission:* {physical.date_emission.strftime('%d/%m/%Y') if physical.date_emission else 'N/A'}\n"
        msg += f"⏳ *Échéance:* {physical.date_echeance.strftime('%d/%m/%Y') if physical.date_echeance else 'N/A'}\n"
        
        # Use first available cashing date
        cashing_date = physical.date_encaissement or next((d.date_encaissement for d in physical.datacheque_ids if d.date_encaissement), None)
        if cashing_date:
            msg += f"✅ *Encaissé le:* {cashing_date.strftime('%d/%m/%Y')}\n"

        msg += f"📊 *État Global:* *{status_label}*\n\n"
        
        if physical.datacheque_ids:
            msg += "🧾 *Répartitions (Paiements) :*\n"
            for d in physical.datacheque_ids:
                # Labels robust fetching
                f_selection = dict(d._fields['facture'].selection or {})
                f_label = f_selection.get(d.facture) or d.facture or "N/A"
                
                t_selection = dict(d._fields['type'].selection or {})
                t_label = t_selection.get(d.type) or d.type or "N/A"
                
                d_status = "✅" if (d.encours == 'encaisse' or d.date_encaissement) else "⏳"
                
                msg += f"• {d.benif_id.name or 'Inconnu'}: *{'{:,.2f}'.format(d.amount).replace(',', ' ')} DH* ({f_label}, {t_label}) {d_status}\n"
                
                # Retrieve and append Google Drive links of this datacheque split
                links = []
                if d.chq_pdf_url:
                    links.append(f"CHQ: {d.chq_pdf_url}")
                if d.doc_pdf_url:
                    links.append(f"DOC: {d.doc_pdf_url}")
                if d.dem_pdf_url:
                    links.append(f"DEM: {d.dem_pdf_url}")
                
                if links:
                    msg += f"  ↳ 🔗 { ' | '.join(links) }\n"
            
        # Direct PDF attachments if available
        physical_full = physical.sudo().with_context(bin_size=False).browse(physical.id)
        files = []
        if physical_full.chq_vide_pdf:
            files.append({
                'pdf_base64': physical_full.chq_vide_pdf.decode('utf-8') if isinstance(physical_full.chq_vide_pdf, bytes) else physical_full.chq_vide_pdf,
                'file_name': physical_full.chq_vide_filename or f"Cheque_Vide_{physical_full.name}.pdf",
                'caption': f"Chèque vide #{physical_full.name}"
            })
        if physical_full.doc_pdf:
            files.append({
                'pdf_base64': physical_full.doc_pdf.decode('utf-8') if isinstance(physical_full.doc_pdf, bytes) else physical_full.doc_pdf,
                'file_name': physical_full.doc_filename or f"Documentation_{physical_full.name}.pdf",
                'caption': f"Documentation #{physical_full.name}"
            })
        if physical_full.cheque_copy_pdf:
            files.append({
                'pdf_base64': physical_full.cheque_copy_pdf.decode('utf-8') if isinstance(physical_full.cheque_copy_pdf, bytes) else physical_full.cheque_copy_pdf,
                'file_name': physical_full.cheque_copy_filename or f"Cheque_{physical_full.name}.pdf",
                'caption': f"Chèque #{physical_full.name}"
            })

        return {
            'status': 'success',
            'response': msg,
            'files': files,
            'product_name': f"Chèque #{physical.name}"
        }
