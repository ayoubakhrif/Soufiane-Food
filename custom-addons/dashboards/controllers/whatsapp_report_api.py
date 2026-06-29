import base64
import logging
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

        if message_text != 'rapport':
            return {'status': 'ignored', 'message': 'Command not recognized.'}

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
            _logger.error(f"Error generating surestarie report: {str(e)}")
            return {'status': 'error', 'response': f"❌ *Erreur lors de la génération du rapport:* {str(e)}"}
