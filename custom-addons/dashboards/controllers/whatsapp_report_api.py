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
            # 1. Fetch Logistique Data
            log_data_list = request.env['surestarie.magasinage.report'].sudo().read_group(
                [],
                ['week', 'container_count:sum', 'surestarie_amount:sum', 'magasinage_amount:sum'],
                ['week']
            )

            # Prepare unified dictionary by week
            weeks_data = defaultdict(lambda: {
                'week': '',
                'container_count': 0,
                'log_surestarie': 0.0,
                'log_magasinage': 0.0,
                'fin_surestarie': 0.0,
                'fin_magasinage': 0.0,
            })

            for log in log_data_list:
                week = log.get('week', False)
                if not week:
                    continue
                w_data = weeks_data[week]
                w_data['week'] = week
                w_data['container_count'] += log.get('container_count', 0)
                w_data['log_surestarie'] += log.get('surestarie_amount', 0.0)
                w_data['log_magasinage'] += log.get('magasinage_amount', 0.0)

            # 2. Fetch Finance Data (Cheques)
            cheques_list = request.env['datacheque'].sudo().search([
                ('type', 'in', ['surestarie', 'magasinage']),
                ('state', '!=', 'annule')
            ])
            for chq in cheques_list:
                week = chq.week
                if not week:
                    continue
                w_data = weeks_data[week]
                w_data['week'] = week
                if chq.type == 'surestarie':
                    w_data['fin_surestarie'] += chq.amount
                elif chq.type == 'magasinage':
                    w_data['fin_magasinage'] += chq.amount

            # 3. Fetch Finance Data (Deductions)
            deductions_list = request.env['finance.deduction.payment'].sudo().search([
                ('type', 'in', ['surestarie', 'magasinage'])
            ])
            for ded in deductions_list:
                if not ded.date:
                    continue
                week = request.env['datacheque'].french_week_number(ded.date)
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

            # Sort by week (descending usually makes sense for reporting)
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
            # 1. Logistique Data
            log_entries = request.env['surestarie.magasinage.report'].sudo().search([
                ('week', '=', target_week)
            ], order='bad_date desc')
            
            log_details = log_entries.read(['bad_date', 'bl_number', 'article_id', 'supplier_id', 'container_count', 'surestarie_amount', 'magasinage_amount'])

            # Fetch the actual logistique.entry to get payment details (cheques, deductions, etc.)
            real_entries = request.env['logistique.entry'].sudo().browse(log_entries.ids)
            entry_map = {e.id: e for e in real_entries}

            totals = {
                'container_count': 0,
                'log_surestarie': 0.0,
                'log_magasinage': 0.0,
                'fin_surestarie': 0.0,
                'fin_magasinage': 0.0,
            }

            for l in log_details:
                totals['container_count'] += l.get('container_count') or 0
                totals['log_surestarie'] += l.get('surestarie_amount') or 0.0
                totals['log_magasinage'] += l.get('magasinage_amount') or 0.0

                # Compute Payment Type & Cheque Numbers
                entry = entry_map.get(l['id'])
                payment_types = []
                if entry:
                    # Chèques
                    chqs = [c.cheque_id.chq for c in entry.cheque_ids if c.type in ('surestarie', 'magasinage') and c.cheque_id.chq]
                    if chqs:
                        payment_types.append(f"Chèque ({', '.join(chqs)})")
                    elif any(c.type in ('surestarie', 'magasinage') for c in entry.cheque_ids):
                        payment_types.append("Chèque")
                    
                    # Déductions
                    if any(d.type in ('surestarie', 'magasinage') for d in entry.deduction_ids):
                        payment_types.append("Déduction")
                        
                    # Virements
                    if any(t.type in ('surestarie', 'magasinage') for t in entry.transfer_ids):
                        payment_types.append("Virement")
                        
                    # Sutra
                    if hasattr(entry, 'sutra_ids') and any(s.type in ('surestarie', 'magasinage') for s in entry.sutra_ids):
                        payment_types.append("Sutra")

                l['payment_info'] = " + ".join(payment_types) if payment_types else "Non spécifié"

            # 2. Finance Cheques
            cheques_list = request.env['datacheque'].sudo().search([
                ('type', 'in', ['surestarie', 'magasinage']),
                ('state', '!=', 'annule'),
                ('week', '=', target_week)
            ], order='date_emission desc')
            
            fin_cheques_details = cheques_list.read(['chq', 'benif_id', 'date_emission', 'type', 'amount'])
            
            for c in fin_cheques_details:
                if c.get('type') == 'surestarie':
                    totals['fin_surestarie'] += c.get('amount', 0.0)
                elif c.get('type') == 'magasinage':
                    totals['fin_magasinage'] += c.get('amount', 0.0)

            # 3. Finance Deductions
            # We can't search directly by 'week' if it's not a stored field on finance.deduction.payment.
            # We must fetch all deductions and filter in python, OR fetch the ones roughly around this month.
            # Since deductions aren't millions, we can fetch all or search by date range. Let's fetch all and filter.
            all_deductions = request.env['finance.deduction.payment'].sudo().search([
                ('type', 'in', ['surestarie', 'magasinage'])
            ], order='date desc')
            
            fin_deductions_details = []
            for ded in all_deductions:
                if not ded.date:
                    continue
                w = request.env['datacheque'].french_week_number(ded.date)
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
