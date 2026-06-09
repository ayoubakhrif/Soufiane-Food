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

        # 4. Detect Specialized Commands (BL or Supplier)
        import re
        
        # A. BL Search: BL (xxx) or BL xxx
        bl_match = re.search(r"(?i)^bl\s*[:(\s]*([A-Z0-9.\-_/]+)[)\s]*$", message_text)
        if bl_match:
            bl_code = bl_match.group(1)
            entry = request.env['logistique.entry'].sudo().search([
                ('bl_number', 'ilike', bl_code)
            ], limit=1, order='id desc')
            
            if entry:
                art_name = entry.achat_article_id.name or entry.article_id.name or "Inconnu"
                eta_val = entry.eta or (entry.dossier_id and entry.dossier_id.eta) or False
                eta_str = eta_val.strftime('%d/%m/%Y') if eta_val else "À venir"
                
                status = "⚓ DÉJÀ SUR PORT" if (eta_val and eta_val < date.today()) else "🚢 EN COURS / À VENIR"
                if entry.port_status == 'exited':
                    status = "✅ SORTI (EXITED)"

                response = (
                    f"📋 *Dossier BL : {entry.bl_number}*\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"📦 *Article* : {art_name.upper()}\n"
                    f"🚢 *Statut* : {status}\n"
                    f"📅 *ETA* : {eta_str}\n"
                    f"🔢 *Quantité* : *{entry.container_count}* conteneurs\n"
                    f"🏗️ *Port* : {entry.port_status}\n"
                )
                return {'status': 'response', 'response': response}
            else:
                return {'status': 'not_found', 'message': f"❌ Aucun dossier trouvé avec le BL '{bl_code}'."}

        # B. Supplier Search: Supplier (name) or suplier name
        # Flexibility: Supplier, Suplier, Suppier, Suuplier
        supp_match = re.search(r"(?i)^(?:supplier|suplier|suppier|suuplier)\s*[:(\s]*([^)]+)\)?$", message_text)
        if supp_match:
            supp_name = supp_match.group(1).strip()
            # Find supplier (direct match or AI fallback)
            supplier = request.env['logistique.supplier'].sudo().search([('name', 'ilike', supp_name)], limit=1)
            
            if not supplier:
                # Optional: Simple AI check for supplier name if direct fails
                return {'status': 'not_found', 'message': f"❌ Fournisseur '{supp_name}' non reconnu."}

            # Find all active dossiers for this supplier
            entries = request.env['logistique.entry'].sudo().search([
                ('supplier_id', '=', supplier.id),
                ('port_status', '=', 'on_port')
            ], order='eta asc')
            
            if not entries:
                return {
                    'status': 'response',
                    'response': f"📋 *Fournisseur : {supplier.name.upper()}*\n\n✅ Aucun dossier 'Sur Port' actuellement pour ce fournisseur."
                }

            # Format Supplier Response
            response = f"📋 *Fournisseur : {supplier.name.upper()}*\n"
            response += f"━━━━━━━━━━━━━━━━━━\n\n"
            
            # Group by Article
            grouped = {}
            for e in entries:
                art = e.achat_article_id.name or e.article_id.name or "Inconnu"
                if art not in grouped: grouped[art] = []
                grouped[art].append(e)
            
            for art, r_entries in grouped.items():
                response += f"🛳️ *{art.upper()}*\n"
                for e in r_entries:
                    eta_val = e.eta or (e.dossier_id and e.dossier_id.eta) or False
                    eta_str = eta_val.strftime('%d/%m') if eta_val else "??"
                    response += f"• BL {e.bl_number or '??'} : *{e.container_count}* cont. (ETA: {eta_str})\n"
                response += "\n"
                
            response += f"_Total : {len(entries)} dossiers sur port_"
            return {'status': 'response', 'response': response}

        # C. Port Status: "port", "au port", "on port", "sur port", etc.
        if message_text.lower() in [
            'port', 'au port', 'on port', 'sur port',
            'dossiers port', 'dossiers au port', 'dossiers sur port', 'dossiers on port'
        ]:
            today = fields.Date.today()
            # Search for dossiers that are currently 'on_port' and have arrived (ETA <= today)
            entries = request.env['logistique.entry'].sudo().search([
                ('port_status', '=', 'on_port'),
                ('eta', '<=', today)
            ], order='eta asc')

            if not entries:
                return {
                    'status': 'response',
                    'response': "⚓ *LOGISTIQUE - PORT*\n\n✅ Aucun dossier n'est actuellement marqué 'Sur Port' avec une arrivée confirmée."
                }

            # Use a dummy record to render the report
            dummy_record = request.env['logistique.entry'].sudo().search([], limit=1)
            pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf('logistique.action_report_logistique_port', res_ids=dummy_record.ids)
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            return {
                'status': 'success',
                'message': "⚓ *DOSSIERS ACTUELLEMENT AU PORT*\nVoici la situation détaillée en format PDF.",
                'pdf_base64': pdf_base64,
                'file_name': f"Situation_Port_{today.strftime('%d_%m_%Y')}.pdf"
            }

        # D. Claims/Souffrance: keywords like "souffrance", "soufrance", "réclamations", "problemes", "claims", "مشاكل", etc.
        claims_keywords = [
            'souffrance', 'soufrance', 'réclamation', 'reclamation', 'problème', 'probleme', 
            'claim', 'complaint', 'مشكل', 'مشاكل', 'شكاوى', 'شكوى', 'شكايات', 'شكاية'
        ]
        if any(keyword in message_text.lower() for keyword in claims_keywords):
            if 'claims.quantity' not in request.env:
                return {
                    'status': 'response',
                    'response': "❌ Le module de réclamations n'est pas activé ou installé sur cette base."
                }
            
            dummy_record = request.env['logistique.entry'].sudo().search([], limit=1)
            if not dummy_record:
                return {
                    'status': 'response',
                    'response': "❌ Aucun dossier logistique n'est disponible pour générer le rapport."
                }
            
            try:
                today = fields.Date.today()
                pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf('claims.action_report_claims_summary', res_ids=dummy_record.ids)
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

                return {
                    'status': 'success',
                    'message': "⚠️ *DOSSIERS EN SOUFFRANCE & RÉCLAMATIONS*\nVoici la situation globale des réclamations actives.",
                    'pdf_base64': pdf_base64,
                    'file_name': f"Situation_Reclamations_{today.strftime('%d_%m_%Y')}.pdf"
                }
            except Exception as e:
                _logger.error(f"Error generating claims summary PDF report: {str(e)}")
                return {
                    'status': 'response',
                    'response': f"❌ Une erreur est survenue lors de la génération du PDF des réclamations : {str(e)}"
                }


        # E. Situation Report: situation W24
        situation_match = re.search(r"(?i)^situation\s+(w\d{2})$", message_text)
        if situation_match:
            week = situation_match.group(1).upper()
            return self._generate_situation_report(week)

        # F. Week Search: W1, Semaine 1, S1, Week 1, etc.
        # Support formats like W1, w01, Semaine 1, semaine-1, S1, Week 1, and optional year like W1 2026, S1/2026, etc.
        week_match = re.search(r"(?i)^\s*(?:week|semaine|s|w)\s*[-_ ]*\s*([0-9]{1,2})(?:\s*[-_/ ]\s*([0-9]{2,4}))?\s*$", message_text)
        if week_match:
            try:
                week_num = int(week_match.group(1))
                year_num = int(week_match.group(2)) if week_match.group(2) else date.today().year
                if len(str(year_num)) == 2:
                    year_num += 2000

                # Validate week number
                if not (1 <= week_num <= 53):
                    return {'status': 'response', 'response': f"❌ Numéro de semaine '{week_num}' invalide. Veuillez entrer une semaine entre 1 et 53."}

                # Calculate start and end dates of the week
                start_date = date.fromisocalendar(year_num, week_num, 1)
                end_date = date.fromisocalendar(year_num, week_num, 7)

                # Search entries with BAD date in this week
                entries = request.env['logistique.entry'].sudo().search([
                    ('bad_date', '>=', start_date),
                    ('bad_date', '<=', end_date)
                ], order='bad_date asc, id asc')

                if not entries:
                    return {
                        'status': 'response',
                        'response': f"📅 *Semaine {week_num} ({year_num})*\n🗓️ *Du {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}*\n\n✅ Aucun BL trouvé avec une date de BAD durant cette semaine."
                    }

                # Format response
                response = f"📅 *Situation Semaine {week_num} ({year_num})*\n"
                response += f"🗓️ *Du {start_date.strftime('%d/%m')} au {end_date.strftime('%d/%m')}*\n"
                response += f"━━━━━━━━━━━━━━━━━━\n\n"

                # Group by Article
                grouped = {}
                for e in entries:
                    art = e.achat_article_id.name or e.article_id.name or "SANS ARTICLE"
                    if art not in grouped:
                        grouped[art] = []
                    grouped[art].append(e)

                total_containers = 0
                for art, r_entries in grouped.items():
                    response += f"🛳️ *{art.upper()}*\n"
                    for e in r_entries:
                        status_lbl = "✅ Sorti" if e.port_status == 'exited' else "⚓ Au Port"
                        bad_str = e.bad_date.strftime('%d/%m') if e.bad_date else "??"
                        supplier_name = e.supplier_id.name or "Inconnu"
                        containers = e.container_count or 0
                        total_containers += containers
                        
                        response += f"• *BL {e.bl_number or '??'}* : *{containers}* cont. | BAD: {bad_str} | Fourn: {supplier_name} | {status_lbl}\n"
                    response += "\n"

                response += f"━━━━━━━━━━━━━━━━━━\n"
                response += f"📊 *Résumé de la semaine :*\n"
                response += f"• Total BLs : *{len(entries)}*\n"
                response += f"• Total conteneurs : *{total_containers}* conteneurs\n"

                return {'status': 'response', 'response': response}

            except ValueError as val_err:
                _logger.error(f"ValueError parsing week query: {str(val_err)}")
                return {'status': 'response', 'response': f"❌ Erreur lors de la détermination de la semaine {week_num} pour l'année {year_num}."}
            except Exception as e:
                _logger.error(f"Error handling week query: {str(e)}")
                return {'status': 'response', 'response': f"❌ Une erreur inattendue est survenue lors de la recherche par semaine."}


        # 4. Search for Article (Fallback - Filter by Active Dossiers Only)
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

    def _generate_situation_report(self, week):
        entries = request.env['logistique.entry'].sudo().search([('week', '=ilike', week)])
        
        if not entries:
            return {
                'status': 'response',
                'response': f"📋 *ÉTAT DE CONTRÔLE : {week}*\n━━━━━━━━━━━━━━━━━━\nAucun dossier trouvé pour cette semaine."
            }
            
        in_progress_entries = entries.filtered(lambda e: e.status == 'in_progress')
        get_out_entries = entries.filtered(lambda e: e.status == 'get_out')
        closed_entries = entries.filtered(lambda e: e.status == 'closed')
        
        response = f"📋 *ÉTAT DE CONTRÔLE : {week}*\n"
        response += "━━━━━━━━━━━━━━━━━━\n\n"
        
        # 1- En cours
        response += f"🚢 *1. EN COURS / AU PORT ({len(in_progress_entries)} dossiers)*\n"
        response += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        for e in in_progress_entries:
            tc_names = e.container_names or "N/A"
            eta_str = e.eta.strftime('%d/%m/%Y') if e.eta else "N/A"
            free_time = e.free_time or 0
            saisi_par = e.saisi_par or "N/A"
            
            response += f"🔹 *BL : {e.bl_number or 'N/A'}*\n"
            response += f"   👤 Saisi par : *{saisi_par}*\n"
            response += f"   📦 TC : *{tc_names}*\n"
            response += f"   📅 ETA : *{eta_str}* | Franchise : *{free_time}j*\n\n"
            
        # 2- Gate Out
        response += f"🚪 *2. GATE OUT / SORTIE DU PORT ({len(get_out_entries)} dossiers)*\n"
        response += "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n"
        for e in get_out_entries:
            bad_str = e.bad_date.strftime('%d/%m/%Y') if e.bad_date else "N/A"
            exit_str = e.exit_date.strftime('%d/%m/%Y') if e.exit_date else "N/A"
            entry_str = e.entry_date.strftime('%d/%m/%Y') if e.entry_date else "N/A"
            saisi_par = e.saisi_par or "N/A"
            
            # Chèques (Supprimer les doublons)
            chq_series = list(set([c.cheque_serie for c in e.cheque_ids if c.cheque_serie]))
            chq_str = ", ".join(chq_series) if chq_series else "Aucun"
            
            thc = f"{e.thc_amount:,.2f}".replace(',', ' ')
            mag = f"{e.magasinage_amount:,.2f}".replace(',', ' ')
            sur = f"{e.surestarie_amount:,.2f}".replace(',', ' ')
            
            response += f"🔹 *BL : {e.bl_number or 'N/A'}*\n"
            response += f"   👤 Saisi par : *{saisi_par}*\n"
            response += f"   🗓️ Dates : BAD *{bad_str}* | Sortie *{exit_str}* | Entrée *{entry_str}*\n"
            response += f"   💰 Frais : THC *{thc} DH* | Mag *{mag} DH* | Sur *{sur} DH*\n"
            response += f"   🧾 Chèques : *{chq_str}*\n\n"
            
        # 3- Dossiers clôturés
        response += f"✅ *3. DOSSIERS CLÔTURÉS* : *{len(closed_entries)}*\n\n"
        
        # 5- Restant (Nombre TC au port)
        # On calcule les restants à partir des dossiers "En cours"
        restant_tc = sum(e.container_count for e in in_progress_entries)
        response += f"📦 *5. RESTANT* : *{restant_tc}* TC au port\n"
        
        return {
            'status': 'response',
            'response': response
        }
