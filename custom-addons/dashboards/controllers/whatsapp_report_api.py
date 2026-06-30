import base64
import logging
import re
from collections import defaultdict
from odoo import http, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppSurestarieReportController(http.Controller):

    @http.route('/api/whatsapp/surestarie_report', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_surestarie_report(self, **kwargs):
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'whatsapp_direct_quantity')
        
        if not api_key or api_key != expected_api_key:
            _logger.warning("Unauthorized access attempt to WhatsApp Surestarie Report API")
            return {'status': 'error', 'message': 'Unauthorized'}

        try:
            data = kwargs
            message_text = data.get('message', '').strip().lower()
            group_id = data.get('group_id', '')
        except Exception as e:
            return {'status': 'error', 'message': f'Invalid JSON: {str(e)}'}

        # Target Group ID
        TARGET_GROUP_ID = '120363410175900080@g.us'
        if group_id != TARGET_GROUP_ID:
            return {'status': 'ignored', 'message': 'Not the correct group.'}

        # Check for specific week request
        week_match = re.match(r'^(?:w|s|semaine|week)\s*0?(\d{1,2})$', message_text)
        
        if message_text == 'rapport':
            return self._generate_global_report()
        elif week_match:
            week_number = int(week_match.group(1))
            target_week = f"W{week_number:02d}"
            return self._generate_week_details_report(target_week)
        else:
            return {'status': 'ignored', 'message': 'Command not recognized.'}

    def _generate_global_report(self):
        try:
            weeks_data = defaultdict(lambda: {
                'week': '',
                'container_count': 0,
                'log_surestarie': 0.0,
                'log_magasinage': 0.0,
                'fin_surestarie': 0.0,
                'fin_magasinage': 0.0,
            })
            
            french_week_number = request.env['datacheque'].french_week_number
            seen_entries_per_week = defaultdict(set)

            # 1. Fetch Logistique Data (by Payment Date)
            def add_log_payment(payment_records):
                for p in payment_records:
                    if not p.date or p.type not in ('surestarie', 'magasinage'):
                        continue
                    week = french_week_number(p.date)
                    if not week:
                        continue
                    w_data = weeks_data[week]
                    w_data['week'] = week
                    if p.type == 'surestarie':
                        w_data['log_surestarie'] += p.amount
                    else:
                        w_data['log_magasinage'] += p.amount
                    
                    if p.entry_id and p.entry_id.id not in seen_entries_per_week[week]:
                        w_data['container_count'] += p.entry_id.container_count or 0
                        seen_entries_per_week[week].add(p.entry_id.id)
            
            add_log_payment(request.env['logistique.dossier.cheque'].sudo().search([('type', 'in', ['surestarie', 'magasinage'])]))
            add_log_payment(request.env['logistique.dossier.deduction'].sudo().search([('type', 'in', ['surestarie', 'magasinage'])]))
            add_log_payment(request.env['logistique.dossier.transfer'].sudo().search([('type', 'in', ['surestarie', 'magasinage'])]))
            add_log_payment(request.env['logistique.dossier.sutra'].sudo().search([('type', 'in', ['surestarie', 'magasinage'])]))

            # 2. Fetch Finance Data (Cheques by Echeance)
            cheques_list = request.env['datacheque'].sudo().search([
                ('type', 'in', ['surestarie', 'magasinage']),
                ('state', '!=', 'annule')
            ])
            for chq in cheques_list:
                # Use date_echeance, fallback to date_emission
                date_to_use = chq.date_echeance or chq.date_emission
                if not date_to_use:
                    continue
                week = french_week_number(date_to_use)
                if not week:
                    continue
                w_data = weeks_data[week]
                w_data['week'] = week
                if chq.type == 'surestarie':
                    w_data['fin_surestarie'] += chq.amount
                elif chq.type == 'magasinage':
                    w_data['fin_magasinage'] += chq.amount

            # 3. Fetch Finance Data (Deductions by Date)
            deductions_list = request.env['finance.deduction.payment'].sudo().search([
                ('type', 'in', ['surestarie', 'magasinage'])
            ])
            for ded in deductions_list:
                if not ded.date:
                    continue
                week = french_week_number(ded.date)
                if not week:
                    continue
                w_data = weeks_data[week]
                w_data['week'] = week
                if ded.type == 'surestarie':
                    w_data['fin_surestarie'] += ded.amount
                elif ded.type == 'magasinage':
                    w_data['fin_magasinage'] += ded.amount

            # 4. Compute Differentials and Averages
            report_data = []
            totals = {
                'container_count': 0,
                'log_surestarie': 0.0,
                'log_magasinage': 0.0,
                'fin_surestarie': 0.0,
                'fin_magasinage': 0.0,
                'diff_surestarie': 0.0,
                'diff_magasinage': 0.0,
            }

            sorted_weeks = sorted(weeks_data.keys(), reverse=True)
            for week in sorted_weeks:
                w_data = weeks_data[week]
                c_count = w_data['container_count']
                
                # Differentials
                diff_sur = w_data['log_surestarie'] - w_data['fin_surestarie']
                diff_mag = w_data['log_magasinage'] - w_data['fin_magasinage']
                w_data['diff_surestarie'] = diff_sur
                w_data['diff_magasinage'] = diff_mag
                
                # Averages
                w_data['avg_surestarie'] = (w_data['log_surestarie'] / c_count) if c_count else 0.0
                w_data['avg_magasinage'] = (w_data['log_magasinage'] / c_count) if c_count else 0.0
                
                report_data.append(w_data)

                # Totals
                totals['container_count'] += c_count
                totals['log_surestarie'] += w_data['log_surestarie']
                totals['log_magasinage'] += w_data['log_magasinage']
                totals['fin_surestarie'] += w_data['fin_surestarie']
                totals['fin_magasinage'] += w_data['fin_magasinage']
                totals['diff_surestarie'] += diff_sur
                totals['diff_magasinage'] += diff_mag

            if totals['container_count'] > 0:
                totals['log_global_avg'] = (totals['log_surestarie'] + totals['log_magasinage']) / totals['container_count']
                totals['fin_global_avg'] = (totals['fin_surestarie'] + totals['fin_magasinage']) / totals['container_count']
                totals['diff_global_avg'] = totals['log_global_avg'] - totals['fin_global_avg']
            else:
                totals['log_global_avg'] = 0.0
                totals['fin_global_avg'] = 0.0
                totals['diff_global_avg'] = 0.0

            report_values = {
                'report_data': report_data,
                'totals': totals
            }

            # 5. Generate PDF
            pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
                'dashboards.action_report_surestarie_compare', [1], data=report_values)
            
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            return {
                'status': 'success',
                'message': "Voici le rapport comparatif Surestarie et Magasinage généré :",
                'pdf_base64': pdf_base64,
                'file_name': 'Rapport_Surestarie.pdf'
            }

        except Exception as e:
            _logger.error(f"Error generating surestarie report: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': f'Erreur interne: {str(e)}'}

    def _generate_week_details_report(self, target_week):
        try:
            french_week_number = request.env['datacheque'].french_week_number
            
            # 1. Logistique Data (Filter by Payment Date)
            target_entry_ids = set()
            payment_types_per_entry = defaultdict(list)
            amounts_per_entry = defaultdict(lambda: {'surestarie': 0.0, 'magasinage': 0.0})

            def process_log_payments(model_name):
                records = request.env[model_name].sudo().search([('type', 'in', ['surestarie', 'magasinage'])])
                for p in records:
                    if not p.date or not getattr(p, 'entry_id', False):
                        continue
                    if french_week_number(p.date) == target_week:
                        entry_id = p.entry_id.id
                        target_entry_ids.add(entry_id)
                        
                        # Add payment type label
                        label = "Autre"
                        if model_name == 'logistique.dossier.cheque':
                            label = f"Chèque ({p.cheque_serie})" if getattr(p, 'cheque_serie', False) else "Chèque"
                        elif model_name == 'logistique.dossier.deduction':
                            label = "Déduction"
                        elif model_name == 'logistique.dossier.transfer':
                            label = "Virement"
                        elif model_name == 'logistique.dossier.sutra':
                            label = "Sutra"
                            
                        if label not in payment_types_per_entry[entry_id]:
                            payment_types_per_entry[entry_id].append(label)
                            
                        # Add amounts
                        if p.type == 'surestarie':
                            amounts_per_entry[entry_id]['surestarie'] += p.amount
                        else:
                            amounts_per_entry[entry_id]['magasinage'] += p.amount

            process_log_payments('logistique.dossier.cheque')
            process_log_payments('logistique.dossier.deduction')
            process_log_payments('logistique.dossier.transfer')
            process_log_payments('logistique.dossier.sutra')
            
            real_entries = request.env['logistique.entry'].sudo().browse(list(target_entry_ids))
            
            totals = {
                'container_count': 0,
                'log_surestarie': 0.0,
                'log_magasinage': 0.0,
                'fin_surestarie': 0.0,
                'fin_magasinage': 0.0,
            }
            
            log_details = []
            for entry in real_entries:
                sur = amounts_per_entry[entry.id]['surestarie']
                mag = amounts_per_entry[entry.id]['magasinage']
                
                # Fetch article from purchase entry if possible, else legacy
                article_name = ''
                article_id = False
                if entry.achat_article_id:
                    article_name = entry.achat_article_id.name
                    article_id = entry.achat_article_id.id
                elif entry.article_id:
                    article_name = entry.article_id.name
                    article_id = entry.article_id.id

                log_details.append({
                    'id': entry.id,
                    'bad_date': entry.bad_date,
                    'bl_number': entry.bl_number,
                    'article_id': [article_id, article_name] if article_id else False,
                    'supplier_id': [entry.supplier_id.id, entry.supplier_id.name] if entry.supplier_id else False,
                    'container_count': entry.container_count,
                    'surestarie_amount': sur,
                    'magasinage_amount': mag,
                    'payment_info': " + ".join(payment_types_per_entry[entry.id]) or "Non spécifié"
                })
                
                totals['container_count'] += entry.container_count or 0
                totals['log_surestarie'] += sur
                totals['log_magasinage'] += mag

            # Sort log_details by bad_date (similar to what the SQL view did)
            log_details = sorted(log_details, key=lambda x: str(x['bad_date']) if x['bad_date'] else '', reverse=True)

            # 2. Finance Cheques
            all_cheques = request.env['datacheque'].sudo().search([
                ('type', 'in', ['surestarie', 'magasinage']),
                ('state', '!=', 'annule')
            ], order='date_emission desc')
            
            fin_cheques_details = []
            for chq in all_cheques:
                date_to_use = chq.date_echeance or chq.date_emission
                if not date_to_use:
                    continue
                if french_week_number(date_to_use) == target_week:
                    fin_cheques_details.append({
                        'chq': chq.chq,
                        'benif_id': [chq.benif_id.id, chq.benif_id.name] if chq.benif_id else False,
                        'date_emission': chq.date_emission,
                        'type': chq.type,
                        'amount': chq.amount
                    })
                    if chq.type == 'surestarie':
                        totals['fin_surestarie'] += chq.amount
                    elif chq.type == 'magasinage':
                        totals['fin_magasinage'] += chq.amount

            # 3. Finance Deductions
            all_deductions = request.env['finance.deduction.payment'].sudo().search([
                ('type', 'in', ['surestarie', 'magasinage'])
            ], order='date desc')
            
            fin_deductions_details = []
            for ded in all_deductions:
                if not ded.date:
                    continue
                w = french_week_number(ded.date)
                if w == target_week:
                    fin_deductions_details.append({
                        'date': ded.date,
                        'benif_id': [ded.benif_id.id, ded.benif_id.name] if ded.benif_id else False,
                        'operation_ref': ded.operation_ref,
                        'bl_id': [ded.bl_id.id, ded.bl_id.name] if ded.bl_id else False,
                        'type': ded.type,
                        'amount': ded.amount
                    })
                    if ded.type == 'surestarie':
                        totals['fin_surestarie'] += ded.amount
                    elif ded.type == 'magasinage':
                        totals['fin_magasinage'] += ded.amount

            report_values = {
                'week_name': target_week,
                'log_details': log_details,
                'fin_cheques_details': fin_cheques_details,
                'fin_deductions_details': fin_deductions_details,
                'totals': totals
            }

            # 4. Generate PDF
            pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
                'dashboards.action_report_surestarie_week_details', [1], data=report_values)
            
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            return {
                'status': 'success',
                'message': f"Voici le rapport détaillé pour la semaine {target_week} :",
                'pdf_base64': pdf_base64,
                'file_name': f'Details_Surestarie_{target_week}.pdf'
            }

        except Exception as e:
            _logger.error(f"Error generating week details report: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': f'Erreur interne (Détails semaine): {str(e)}'}
