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

        # 3.2 Handle Situation / Encours Logic
        msg_clean = message_text.lower().strip()
        is_situation_cmd = msg_clean == "situation" or msg_clean.startswith("situation ")
        is_encours_cmd = msg_clean in ["encours", "en cours"] or msg_clean.startswith("encours ") or msg_clean.startswith("en cours ")
        
        # Check if they want the global situation grouped by beneficiary
        benif_triggers = [
            "situation beneficiaire", "situation bénéficiaire", 
            "situation benif", "situation benef",
            "beneficiaires", "bénéficiaires", "benficiaires",
            "benifs", "benif"
        ]
        is_benif_situation_cmd = (msg_clean in benif_triggers) or any(t in msg_clean for t in ["situation beneficiaire", "situation bénéficiaire", "situation benif", "situation benef", "situation benifs"])

        if is_benif_situation_cmd or is_situation_cmd or is_encours_cmd:
            try:
                # Extract state filter if provided (e.g., "situation annule")
                state_filter = None
                if is_situation_cmd and not is_benif_situation_cmd:
                    possible_states = {
                        "actif": "actif", "actifs": "actif",
                        "reserve": "reserve", "réserve": "reserve", "reserves": "reserve",
                        "bureau": "bureau",
                        "annule": "annule", "annulé": "annule", "annulés": "annule",
                        "encaissé": "encaisse", "encaisse": "encaisse", "encaisses": "encaisse", "encaissés": "encaisse"
                    }
                    parts = msg_clean.split()
                    for p in parts[1:]:
                        if p in possible_states:
                            state_filter = possible_states[p]
                            break

                # Set dynamic configuration based on command type
                by_benif = is_benif_situation_cmd
                encours_only = is_encours_cmd and not by_benif
                
                data_arg = {}
                if encours_only:
                    data_arg['encours_only'] = True
                if by_benif:
                    data_arg['by_benif'] = True
                if state_filter:
                    data_arg['state_filter'] = state_filter
                
                # 1. Render QWeb PDF report
                report_action = request.env['ir.actions.report'].sudo()
                pdf_content, _ = report_action._render_qweb_pdf('finance.action_report_finance_situation', res_ids=[], data=data_arg)
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

                # 2. Render Excel spreadsheet using report parser helper
                report_obj = request.env['report.finance.report_finance_situation_template'].sudo()
                report_values = report_obj._get_report_values([], data=data_arg)
                xlsx_base64 = report_obj.generate_excel_data(report_values)

                active_count = report_values.get('total_active_count', 0)
                reserve_count = report_values.get('total_reserve_count', 0)
                bureau_count = report_values.get('total_bureau_count', 0)
                annule_count = report_values.get('total_annule_count', 0)

                if state_filter:
                    state_display = state_filter.capitalize()
                    title_msg = f"📋 *Situation des Chèques ({state_display})* 📋"
                    caption_pdf = f"Situation {state_display} - Version PDF 📄"
                    caption_xlsx = f"Situation {state_display} - Version Excel 📊"
                    file_prefix = f"Situation_{state_display}"
                    prod_name = f"Situation {state_display}"
                elif by_benif:
                    title_msg = "📋 *Situation des Chèques par Bénéficiaire* 📋"
                    caption_pdf = "Situation par Bénéficiaire - Version PDF 📄"
                    caption_xlsx = "Situation par Bénéficiaire - Version Excel 📊"
                    file_prefix = "Situation_Beneficiaires"
                    prod_name = "Situation Bénéficiaires"
                elif encours_only:
                    title_msg = "📋 *Situation des Chèques En Cours (Non Encaissés)* 📋"
                    caption_pdf = "Chèques En Cours - Version PDF 📄"
                    caption_xlsx = "Chèques En Cours - Version Excel 📊"
                    file_prefix = "Encours_Cheques"
                    prod_name = "Chèques En Cours"
                else:
                    title_msg = "📋 *Situation Générale des Chèques* 📋"
                    caption_pdf = "Situation des Chèques - Version PDF 📄"
                    caption_xlsx = "Situation des Chèques - Version Excel 📊"
                    file_prefix = "Situation_Cheques"
                    prod_name = "Situation Générale"

                summary_msg = (
                    f"{title_msg}\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"📊 *Résumé des États* :\n"
                    f"• 🟢 *Actifs* : {active_count} chèques\n"
                    f"• 🟡 *Réserve* : {reserve_count} chèques\n"
                    f"• 🔵 *Bureau* : {bureau_count} chèques\n"
                    f"• 🔴 *Annulés* : {annule_count} chèques\n\n"
                )

                active_talons = request.env['finance.talon'].sudo().search([('etat', '=', 'actif')], order='ste_id asc')
                if active_talons:
                    summary_msg += "🧾 *Derniers chèques sortis* :\n"
                    for talon in active_talons:
                        chq_val = talon.last_used_chq if talon.last_used_chq else "Aucun"
                        summary_msg += f"• {talon.ste_id.name} : *{chq_val}*\n"
                    summary_msg += "\n"

                summary_msg += f"📂 _Les rapports PDF et Excel détaillés ont été générés et sont joints ci-dessous._"

                from odoo import fields
                today_str = fields.Date.today().strftime('%d/%m/%Y').replace('/', '_')
                return {
                    'status': 'success',
                    'product_name': prod_name,
                    'response': summary_msg,
                    'files': [
                        {
                            'pdf_base64': pdf_base64,
                            'file_name': f"{file_prefix}_{today_str}.pdf",
                            'caption': caption_pdf
                        },
                        {
                            'pdf_base64': xlsx_base64,
                            'file_name': f"{file_prefix}_{today_str}.xlsx",
                            'caption': caption_xlsx
                        }
                    ]
                }
            except Exception as e:
                _logger.error(f"Error generating Situation/Encours report: {str(e)}")
                return {'status': 'error', 'message': f"Erreur lors de la génération du rapport : {str(e)}"}

        # 4. Handle Talon Logic
        msg_clean = message_text.lower().strip()
        is_global_talon = False
        talon_state_filter = None
        state_label_fr = "Tous"
        
        if msg_clean in ["talon", "talons"]:
            is_global_talon = True
        elif msg_clean in ["talon coffre", "talons coffre", "talon en coffre", "talons en coffre"]:
            is_global_talon = True
            talon_state_filter = "coffre"
            state_label_fr = "en Coffre"
        elif msg_clean in ["talon actif", "talons actifs", "talon actifs"]:
            is_global_talon = True
            talon_state_filter = "actif"
            state_label_fr = "Actifs"
        elif msg_clean in ["talon cloture", "talons clotures", "talon clotures", "talon cloturé", "talon clôturé", "talons cloturés", "talons clôturés"]:
            is_global_talon = True
            talon_state_filter = "cloture"
            state_label_fr = "Cloturés"

        if is_global_talon:
            try:
                data_arg = {}
                if talon_state_filter:
                    data_arg['talon_state_filter'] = talon_state_filter

                # 1. Render QWeb PDF report
                report_action = request.env['ir.actions.report'].sudo()
                pdf_content, _ = report_action._render_qweb_pdf('finance.action_report_finance_talons_global', res_ids=[], data=data_arg)
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

                # 2. Render Excel spreadsheet using parser helper
                report_obj = request.env['report.finance.report_finance_talons_global_template'].sudo()
                report_values = report_obj._get_report_values([], data=data_arg)
                xlsx_base64 = report_obj.generate_excel_data(report_values)

                total_count = report_values.get('total_talons_count', 0)
                total_coffre = report_values.get('total_coffre_count', 0)
                total_actif = report_values.get('total_actif_count', 0)
                total_cloture = report_values.get('total_cloture_count', 0)
                total_missing = report_values.get('total_missing_chqs', 0)

                title_msg = f"📋 *Rapport Global des Talons ({state_label_fr})* 📋"
                caption_pdf = f"Rapport Talons {state_label_fr} - PDF 📄"
                caption_xlsx = f"Rapport Talons {state_label_fr} - Excel 📊"
                file_prefix = f"Rapport_Talons_{state_label_fr.replace(' ', '_')}"

                summary_msg = (
                    f"{title_msg}\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"📊 *Résumé des Talons* :\n"
                    f"• 📁 *Total* : {total_count} talons\n"
                )
                if not talon_state_filter:
                    summary_msg += (
                        f"• 🔵 *En Coffre* : {total_coffre} talons\n"
                        f"• 🟢 *Actifs* : {total_actif} talons\n"
                        f"• 🔴 *Cloturés* : {total_cloture} talons\n"
                    )
                summary_msg += f"• ⚠️ *Chèques absents* : {total_missing} chèques\n\n"
                summary_msg += f"📂 _Les rapports PDF et Excel détaillés ont été générés et sont joints ci-dessous._"

                from odoo import fields
                today_str = fields.Date.today().strftime('%d/%m/%Y').replace('/', '_')
                return {
                    'status': 'success',
                    'product_name': f"Rapport Talons {state_label_fr}",
                    'response': summary_msg,
                    'files': [
                        {
                            'pdf_base64': pdf_base64,
                            'file_name': f"{file_prefix}_{today_str}.pdf",
                            'caption': caption_pdf
                        },
                        {
                            'pdf_base64': xlsx_base64,
                            'file_name': f"{file_prefix}_{today_str}.xlsx",
                            'caption': caption_xlsx
                        }
                    ]
                }
            except Exception as e:
                _logger.error(f"Error generating Global Talons report: {str(e)}")
                return {'status': 'error', 'message': f"Erreur lors de la génération du rapport : {str(e)}"}

        elif message_text.lower().startswith("talon"):
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

        # 4.5 Handle "dernier chèque"
        if msg_clean in ["dernier cheque", "dernier chèque", "derniers cheques", "derniers chèques"]:
            active_talons = request.env['finance.talon'].sudo().search([('etat', '=', 'actif')], order='ste_id asc')
            if not active_talons:
                return {'status': 'not_found', 'message': "✅ Aucun talon actif trouvé."}
            msg = "📄 *Derniers chèques par talon actif*\n\n"
            for t in active_talons:
                msg += f"• *{t.ste_id.name}* : {t.last_used_chq or 'Aucun'}\n"
            return {'status': 'success', 'response': msg}

        # 5. Handle Cheque / Effet Number Search
        import re
        is_direct_search = False
        search_number = None
        
        # A. Check if numeric (Direct Search)
        if message_text.isdigit():
            is_direct_search = True
            search_number = message_text
        
        # B. Check if it's a choice result like "CHQ 2102572 (Company A)"
        match_chq = re.match(r"CHQ (\d{7}) \((.+)\)", message_text)
        if match_chq:
            cheque_number = match_chq.group(1)
            company_name = match_chq.group(2)
            cheque = request.env['finance.cheque.physical'].sudo().search([
                ('name', '=', cheque_number),
                ('ste_id.name', '=', company_name)
            ], limit=1)
            if cheque:
                return self._format_physical_cheque_details(cheque)

        # C. Check if it's a choice result like "EFFET 123 (Company A)"
        match_effet = re.match(r"EFFET (\d+) \((.+)\)", message_text)
        if match_effet:
            effet_number = match_effet.group(1)
            company_name = match_effet.group(2)
            effet = request.env['finance.effet'].sudo().search([
                ('serie', '=', effet_number),
                ('ste_id.name', '=', company_name)
            ], limit=1)
            if effet:
                return self._format_effet_details(effet)

        if is_direct_search:
            # Search for PHYSICAL cheques and EFFETS
            cheques = request.env['finance.cheque.physical'].sudo().search([('name', '=', search_number)])
            effets = request.env['finance.effet'].sudo().search([('serie', '=', search_number)])
            
            total_matches = len(cheques) + len(effets)
            
            if total_matches == 1:
                if cheques:
                    return self._format_physical_cheque_details(cheques[0])
                elif effets:
                    return self._format_effet_details(effets[0])
            elif total_matches > 1:
                choices = []
                for c in cheques:
                    choices.append(f"CHQ {c.name} ({c.ste_id.name})")
                for e in effets:
                    choices.append(f"EFFET {e.serie} ({e.ste_id.name})")
                    
                choices_text = f"Le numéro *{search_number}* correspond à plusieurs documents. Veuillez choisir :\n"
                for i, choice in enumerate(choices, 1):
                    choices_text += f"{i}- {choice}\n"
                
                return {
                    'status': 'multiple_choices',
                    'message': choices_text,
                    'choices': choices
                }

        # 5.2 Handle Amount Search
        is_amount = False
        amount_val = 0.0
        try:
            clean_amt = message_text.replace(' ', '').replace(',', '.')
            amount_val = float(clean_amt)
            is_amount = True
        except ValueError:
            pass

        if is_amount and amount_val > 0:
            phys_amount = request.env['finance.cheque.physical'].sudo().search([('amount_total', '=', amount_val)], order='date_emission desc', limit=30)
            if phys_amount:
                if len(phys_amount) == 1:
                    return self._format_physical_cheque_details(phys_amount[0])
                else:
                    unique_choices = []
                    choices_text = f"Plusieurs chèques trouvés avec le montant *{'{:,.2f}'.format(amount_val).replace(',', ' ')} DH*. Veuillez choisir :\n"
                    idx = 1
                    for c in phys_amount:
                        choice_txt = f"CHQ {c.name} ({c.ste_id.name})"
                        if choice_txt not in unique_choices:
                            unique_choices.append(choice_txt)
                            
                    effets_amount = request.env['finance.effet'].sudo().search([('montant', '=', amount_val)], order='date_emission desc', limit=30)
                    for e in effets_amount:
                        choice_txt = f"EFFET {e.serie} ({e.ste_id.name})"
                        if choice_txt not in unique_choices:
                            unique_choices.append(choice_txt)
                            
                    if len(unique_choices) == 1:
                        if phys_amount:
                            return self._format_physical_cheque_details(phys_amount[0])
                        elif effets_amount:
                            return self._format_effet_details(effets_amount[0])
                    elif len(unique_choices) > 1:
                        choices_text = f"Plusieurs documents trouvés avec le montant *{'{:,.2f}'.format(amount_val).replace(',', ' ')} DH*. Veuillez choisir :\n"
                        for idx, choice in enumerate(unique_choices, 1):
                            choices_text += f"{idx}- {choice}\n"
                        return {
                            'status': 'multiple_choices',
                            'message': choices_text,
                            'choices': unique_choices
                        }
        # 5.3 Handle Facture (Invoice) Search
        if len(message_text) > 1:
            facture_cheques = request.env['datacheque'].sudo().search([('serie', '=ilike', message_text)], limit=50)
            if facture_cheques:
                physicals = facture_cheques.mapped('physical_cheque_id').filtered(lambda c: c)
                if physicals:
                    if len(physicals) == 1:
                        return self._format_physical_cheque_details(physicals[0])
                    else:
                        unique_choices = []
                        choices_text = f"La facture *{message_text}* est payée par plusieurs chèques. Veuillez choisir :\n"
                        idx = 1
                        for c in physicals:
                            choice_txt = f"CHQ {c.name} ({c.ste_id.name})"
                            if choice_txt not in unique_choices:
                                unique_choices.append(choice_txt)
                                choices_text += f"{idx}- {choice_txt}\n"
                                idx += 1
                        return {
                            'status': 'multiple_choices',
                            'message': choices_text,
                            'choices': unique_choices
                        }

        # 5.5 Handle Week Search
        week_match = re.match(r"^(?:w|s|semaine|week)\s*0*(\d{1,2})$", msg_clean)
        if week_match:
            week_num = int(week_match.group(1))
            week_str = f"W{week_num:02d}"
            
            datacheques = request.env['datacheque'].sudo().search([('week', '=', week_str)], order='journal asc')
            effets = request.env['finance.effet'].sudo().search([('week', '=', week_str)])
            
            if not datacheques and not effets:
                return {'status': 'not_found', 'message': f"Aucun document trouvé pour la semaine {week_str}."}

            documents = []
            total_amount = 0.0
            
            # Group datacheques by physical cheque
            grouped_dqs = {}
            for dq in datacheques:
                phys = dq.physical_cheque_id
                if not phys:
                    continue
                if phys not in grouped_dqs:
                    grouped_dqs[phys] = []
                grouped_dqs[phys].append(dq)
                total_amount += dq.amount
                
            def get_min_journal(dqs_list):
                journals = [dq.journal for dq in dqs_list if dq.journal]
                return min(journals) if journals else float('inf')
                
            for phys, dqs in grouped_dqs.items():
                documents.append({
                    'type_doc': 'CHQ',
                    'obj': phys,
                    'items': dqs,
                    'min_journal': get_min_journal(dqs)
                })
                
            for e in effets:
                documents.append({
                    'type_doc': 'EFFET',
                    'obj': e,
                    'items': [e],
                    'min_journal': float('inf') # Display effets at the bottom
                })
                total_amount += e.montant
                
            # Sort documents by journal
            documents.sort(key=lambda d: d['min_journal'])

            html_content = f"""
            <html>
                <head>
                    <meta charset="utf-8"/>
                    <style>
                        body {{ font-family: sans-serif; font-size: 14px; color: #333; }}
                        h2 {{ text-align: center; color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }}
                        table {{ border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 13px; }}
                        th, td {{ border: 1px solid #bdc3c7; padding: 8px 10px; text-align: left; vertical-align: middle; }}
                        th {{ background-color: #ecf0f1; font-weight: bold; color: #2c3e50; }}
                        .total {{ text-align: right; margin-top: 20px; font-size: 18px; color: #2c3e50; font-weight: bold; }}
                        .chq-info {{ font-weight: bold; color: #2980b9; }}
                        .effet-info {{ font-weight: bold; color: #8e44ad; }}
                    </style>
                </head>
                <body>
                    <h2>Documents de la Semaine {week_str}</h2>
                    <table>
                        <tr style="background-color: #ecf0f1;">
                            <th>Document</th>
                            <th>Date d'émission</th>
                            <th>Société</th>
                            <th>N° Journal</th>
                            <th>Bénéficiaire</th>
                            <th>Série de Facture</th>
                            <th>Type</th>
                            <th>Statut</th>
                            <th>Montant (DH)</th>
                            <th>Montant Global (DH)</th>
                            <th>État Global</th>
                        </tr>
            """
            
            for doc in documents:
                if doc['type_doc'] == 'CHQ':
                    phys = doc['obj']
                    dqs = doc['items']
                    
                    doc_name = phys.name or "N/A"
                    ste_name = phys.ste_id.name if phys.ste_id else "N/A"
                    phys_amount = '{:,.2f}'.format(phys.amount_total).replace(',', ' ')
                    date_em = phys.date_emission.strftime('%d/%m/%Y') if phys.date_emission else "N/A"
                    
                    is_encaisse = phys.encours == 'encaisse' or any(d.date_encaissement for d in phys.datacheque_ids)
                    etat_label = "<span style='color:green; font-weight:bold;'>Encaissé</span>" if is_encaisse else "<span style='color:#e67e22; font-weight:bold;'>En cours</span>"
                    doc_display = f"<div class='chq-info'>CHQ {doc_name}</div>"
                    
                    grouped_rows = []
                    for dq in dqs:
                        journal_val = str(dq.journal) if dq.journal else "N/A"
                        benif_name = dq.benif_id.name if dq.benif_id else "N/A"
                        serie_val = str(dq.serie) if dq.serie else "N/A"
                        t_selection = dict(dq._fields['type'].selection or {})
                        t_label = t_selection.get(dq.type) or dq.type or "N/A"
                        s_selection = dict(dq._fields['state'].selection or {})
                        s_label = s_selection.get(dq.state) or dq.state or "N/A"
                        dq_amount = '{:,.2f}'.format(dq.amount).replace(',', ' ')
                        
                        if grouped_rows and grouped_rows[-1]['journal'] == journal_val and grouped_rows[-1]['benif'] == benif_name:
                            grouped_rows[-1]['items'].append({'type': t_label, 'state': s_label, 'amount': dq_amount, 'serie': serie_val})
                        else:
                            grouped_rows.append({
                                'journal': journal_val,
                                'benif': benif_name,
                                'items': [{'type': t_label, 'state': s_label, 'amount': dq_amount, 'serie': serie_val}]
                            })
                            
                else: # EFFET
                    e = doc['obj']
                    doc_name = e.serie or "N/A"
                    ste_name = e.ste_id.name if e.ste_id else "N/A"
                    phys_amount = '{:,.2f}'.format(e.montant).replace(',', ' ')
                    date_em = e.date_emission.strftime('%d/%m/%Y') if e.date_emission else "N/A"
                    
                    is_encaisse = e.state == 'encaisse'
                    etat_label = "<span style='color:green; font-weight:bold;'>Encaissé</span>" if is_encaisse else "<span style='color:#e67e22; font-weight:bold;'>En cours</span>"
                    doc_display = f"<div class='effet-info'>EFFET {doc_name}</div>"
                    
                    benif_name = e.benif_id.name if e.benif_id else "N/A"
                    
                    grouped_rows = [{
                        'journal': 'N/A',
                        'benif': benif_name,
                        'items': [{'type': 'Effet', 'state': e.state or "N/A", 'amount': phys_amount, 'serie': 'N/A'}]
                    }]
                
                phys_rowspan = sum(len(group['items']) for group in grouped_rows)
                
                first_group = True
                for group in grouped_rows:
                    group_rowspan = len(group['items'])
                    first_item = True
                    for item in group['items']:
                        html_content += "<tr>"
                        if first_group and first_item:
                            html_content += f"""
                                <td rowspan="{phys_rowspan}">{doc_display}</td>
                                <td rowspan="{phys_rowspan}">{date_em}</td>
                                <td rowspan="{phys_rowspan}">{ste_name}</td>
                            """
                        if first_item:
                            html_content += f"""
                                <td rowspan="{group_rowspan}">{group['journal']}</td>
                                <td rowspan="{group_rowspan}">{group['benif']}</td>
                            """
                        html_content += f"""
                                <td>{item['serie']}</td>
                                <td>{item['type']}</td>
                                <td>{item['state']}</td>
                                <td>{item['amount']}</td>
                        """
                        if first_group and first_item:
                            html_content += f"""
                                <td rowspan="{phys_rowspan}"><strong>{phys_amount}</strong></td>
                                <td rowspan="{phys_rowspan}">{etat_label}</td>
                            """
                        html_content += "</tr>"
                        first_item = False
                    first_group = False

            total_str = '{:,.2f}'.format(total_amount).replace(',', ' ')
            html_content += f"""
                    </table>
                    <div class="total">Total de la semaine: {total_str} DH</div>
                </body>
            </html>
            """

            report_action = request.env['ir.actions.report'].sudo()
            try:
                pdf_content = report_action._run_wkhtmltopdf([html_content])
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

                return {
                    'status': 'success',
                    'product_name': f"Chèques Semaine {week_str}",
                    'response': f"Voici le rapport des chèques pour la semaine *{week_str}*.",
                    'files': [
                        {
                            'pdf_base64': pdf_base64,
                            'file_name': f"Cheques_{week_str}.pdf",
                            'caption': f"Chèques de la semaine {week_str} 📄"
                        }
                    ]
                }
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                _logger.error(f"Error generating week PDF: {error_trace}")
                return {'status': 'error', 'message': f"Erreur lors de la génération du PDF ({week_str}) : {str(e)}\n\nTrace: {error_trace}"}

        # 5.6 Handle Manque Search (Missing PDFs)
        if msg_clean == "manque" or msg_clean.startswith("manque "):
            param = msg_clean[6:].strip()
            domain = []
            filter_desc = "globale"

            if param:
                week_match = re.match(r"^(?:w|s|semaine|week)\s*0*(\d{1,2})$", param)
                if week_match:
                    week_num = int(week_match.group(1))
                    week_str = f"W{week_num:02d}"
                    domain.append(('datacheque_ids.week', '=', week_str))
                    filter_desc = f"pour la semaine {week_str}"
                else:
                    domain.append(('ste_id.name', 'ilike', param))
                    filter_desc = f"pour la société '{param}'"

            # Search cheques with missing PDFs
            domain.extend(['|', ('doc_pdf', '=', False), ('chq_vide_pdf', '=', False)])
            
            phys_cheques = request.env['finance.cheque.physical'].sudo().search(domain, order='date_emission desc', limit=100)
            
            if not phys_cheques:
                return {'status': 'not_found', 'message': f"✅ Aucun chèque manquant de PDF trouvé ({filter_desc})."}
            
            msg = f"📄 *Chèques avec PDF manquants ({filter_desc})*\n\n"
            count = 0
            excel_data = []
            for phys in phys_cheques:
                missing = []
                phys_check = phys.sudo().with_context(bin_size=True)
                if not phys_check.doc_pdf:
                    missing.append("Documentation")
                if not phys_check.chq_vide_pdf:
                    missing.append("Chèque vide")
                
                if missing:
                    ste_name = phys.ste_id.name if phys.ste_id else 'N/A'
                    factures = ", ".join(filter(None, [d.serie for d in phys.datacheque_ids]))
                    
                    fact_display = f" [Série de facture: {factures}]" if factures else ""
                    msg += f"• *{phys.name}*{fact_display} ({ste_name}) ❌ Manque : {', '.join(missing)}\n"
                    
                    excel_data.append({
                        'chq': phys.name or "",
                        'ste': ste_name,
                        'facture': factures,
                        'benif': phys.benif_id.name if phys.benif_id else "",
                        'montant': phys.amount_total or 0.0,
                        'date': str(phys.date_emission) if phys.date_emission else "",
                        'manque': ", ".join(missing)
                    })
                    count += 1
            
            if count == 0:
                return {'status': 'not_found', 'message': f"✅ Aucun chèque manquant de PDF trouvé ({filter_desc})."}

            if len(phys_cheques) == 100:
                msg += "\n⚠️ _Seuls les 100 premiers résultats sont affichés._"
                
            # Generate Excel
            import io
            import xlsxwriter
            
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            sheet = workbook.add_worksheet('Manque PDF')
            
            headers = ["N° Chèque", "Société", "Série de facture", "Bénéficiaire", "Montant", "Date Emission", "Manque"]
            for col, h in enumerate(headers):
                sheet.write(0, col, h)
                
            for row_idx, data_row in enumerate(excel_data, 1):
                sheet.write(row_idx, 0, data_row['chq'])
                sheet.write(row_idx, 1, data_row['ste'])
                sheet.write(row_idx, 2, data_row['facture'])
                sheet.write(row_idx, 3, data_row['benif'])
                sheet.write(row_idx, 4, data_row['montant'])
                sheet.write(row_idx, 5, data_row['date'])
                sheet.write(row_idx, 6, data_row['manque'])
                
            workbook.close()
            xlsx_base64 = base64.b64encode(output.getvalue()).decode('utf-8')

            return {
                'status': 'success',
                'product_name': f"Chèques manquants",
                'response': msg,
                'files': [
                    {
                        'pdf_base64': xlsx_base64,
                        'file_name': f"Manque_Cheques.xlsx",
                        'caption': f"Détails des chèques manquants {filter_desc}"
                    }
                ]
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
            if talon.last_used_chq:
                summary_msg += f"\n• Dernier chèque sorti: *{talon.last_used_chq}*"

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

            # Append company-wise breakdown if available
            breakdown_data = benif.get_financial_breakdown()
            if breakdown_data:
                summary_msg += "\n\n🏢 *Chiffres par Société* :\n"
                for b_item in breakdown_data:
                    summary_msg += (
                        f"• *{b_item['ste']}* :\n"
                        f"   ↳ Total: {b_item['count_total']} chqs ({'{:,.2f}'.format(b_item['total']).replace(',', ' ')} DH)\n"
                        f"   ↳ Encaissés: {b_item['count_encaisse']} chqs ({'{:,.2f}'.format(b_item['encaisse']).replace(',', ' ')} DH)\n"
                        f"   ↳ Restants: {b_item['count_non_encaisse']} chqs ({'{:,.2f}'.format(b_item['non_encaisse']).replace(',', ' ')} DH)\n"
                    )

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
