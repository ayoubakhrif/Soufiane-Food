from odoo import models, fields, api
import base64
import io
import logging

_logger = logging.getLogger(__name__)

class ReportFinanceTalonsGlobal(models.AbstractModel):
    _name = 'report.finance.report_finance_talons_global_template'
    _description = 'Rapport Global des Talons Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        domain = []
        state_filter = data.get('talon_state_filter') if data else None
        
        if state_filter:
            domain.append(('etat', '=', state_filter))
            
        talon_recs = self.env['finance.talon'].sudo().search(domain)
        
        # General counters
        total_talons_count = len(talon_recs)
        total_coffre_count = len(talon_recs.filtered(lambda t: t.etat == 'coffre'))
        total_actif_count = len(talon_recs.filtered(lambda t: t.etat == 'actif'))
        total_cloture_count = len(talon_recs.filtered(lambda t: t.etat == 'cloture'))
        
        total_chqs_count = sum(t.num_chq for t in talon_recs)
        total_used_chqs = sum(t.used_chqs for t in talon_recs)
        total_unused_chqs = sum(t.unused_chqs for t in talon_recs)
        total_missing_chqs = sum(t.missing_chqs for t in talon_recs)
        avg_usage_percentage = (total_used_chqs / total_chqs_count * 100) if total_chqs_count else 0.0

        # Grouping by Company (ste)
        ste_summary = {}
        for talon in talon_recs:
            ste = talon.ste_id.name or 'Inconnu'
            if ste not in ste_summary:
                ste_summary[ste] = {
                    'ste_name': ste,
                    'talons': [],
                    'count_total': 0,
                    'count_coffre': 0,
                    'count_actif': 0,
                    'count_cloture': 0,
                    'total_chqs': 0,
                    'used_chqs': 0,
                    'unused_chqs': 0,
                    'missing_chqs': 0,
                }
            
            state_label = dict(talon._fields['etat'].selection).get(talon.etat, talon.etat)
            
            ste_summary[ste]['talons'].append({
                'name_shown': talon.name_shown,
                'name': talon.name,
                'serie': talon.serie,
                'total': talon.num_chq,
                'used': talon.used_chqs,
                'remaining': talon.unused_chqs,
                'missing': talon.missing_chqs,
                'percentage': round(talon.usage_percentage, 1),
                'state_label': state_label,
                'etat': talon.etat,
                'last_used': talon.last_used_chq or 'Aucun',
            })
            
            ste_summary[ste]['count_total'] += 1
            if talon.etat == 'coffre':
                ste_summary[ste]['count_coffre'] += 1
            elif talon.etat == 'actif':
                ste_summary[ste]['count_actif'] += 1
            elif talon.etat == 'cloture':
                ste_summary[ste]['count_cloture'] += 1
            
            ste_summary[ste]['total_chqs'] += talon.num_chq
            ste_summary[ste]['used_chqs'] += talon.used_chqs
            ste_summary[ste]['unused_chqs'] += talon.unused_chqs
            ste_summary[ste]['missing_chqs'] += talon.missing_chqs

        # Sort talons inside each company by name/num
        for ste_name, info in ste_summary.items():
            try:
                info['talons'].sort(key=lambda x: (x['name'] or '', x['serie'] or ''))
            except Exception:
                pass
                
        # Sort companies alphabetically
        sorted_ste_list = sorted(list(ste_summary.values()), key=lambda x: x['ste_name'])

        state_label_fr = "Tous"
        if state_filter == "coffre":
            state_label_fr = "en Coffre"
        elif state_filter == "actif":
            state_label_fr = "Actifs"
        elif state_filter == "cloture":
            state_label_fr = "Cloturés"

        res = {
            'doc_ids': docids,
            'doc_model': 'finance.talon',
            'state_filter': state_filter,
            'state_label_fr': state_label_fr,
            
            'total_talons_count': total_talons_count,
            'total_coffre_count': total_coffre_count,
            'total_actif_count': total_actif_count,
            'total_cloture_count': total_cloture_count,
            
            'total_chqs_count': total_chqs_count,
            'total_used_chqs': total_used_chqs,
            'total_unused_chqs': total_unused_chqs,
            'total_missing_chqs': total_missing_chqs,
            'avg_usage_percentage': avg_usage_percentage,
            
            'ste_summary': sorted_ste_list,
            'report_date': fields.Date.today().strftime('%d/%m/%Y'),
            'report_title': f"Rapport Global des Talons ({state_label_fr})",
        }

        # Generate charts
        res['charts'] = self._generate_base64_charts(res)
        return res

    def _generate_base64_charts(self, values):
        charts_b64 = {
            'state_pie': '',
            'company_bar': ''
        }

        try:
            import matplotlib
            try:
                matplotlib.use('Agg')
            except Exception:
                pass
            import matplotlib.pyplot as plt
            
            # 1. State Distribution Pie Chart (only if not filtered on single state)
            if not values.get('state_filter'):
                state_counts = {
                    'COFFRE': values.get('total_coffre_count', 0),
                    'ACTIF': values.get('total_actif_count', 0),
                    'CLOTURÉ': values.get('total_cloture_count', 0)
                }
                state_counts = {k: v for k, v in state_counts.items() if v > 0}
                if state_counts:
                    labels = list(state_counts.keys())
                    counts = list(state_counts.values())
                    
                    state_colors = {
                        'COFFRE': '#1A73E8', # Blue
                        'ACTIF': '#137333',  # Green
                        'CLOTURÉ': '#D93025' # Red
                    }
                    colors = [state_colors.get(lbl, '#7F8C8D') for lbl in labels]

                    fig, ax = plt.subplots(figsize=(5, 4.5), dpi=120)
                    wedges, texts, autotexts = ax.pie(
                        counts, 
                        labels=labels, 
                        autopct='%1.1f%%',
                        startangle=140, 
                        colors=colors,
                        textprops=dict(color="black", fontsize=8)
                    )
                    plt.setp(autotexts, size=8, weight="bold")
                    ax.set_title("Répartition des Talons par État", fontsize=10, fontweight='bold', color='#1A4D80', pad=10)
                    fig.tight_layout()

                    buf = io.BytesIO()
                    fig.savefig(buf, format='png', bbox_inches='tight', transparent=True)
                    buf.seek(0)
                    charts_b64['state_pie'] = base64.b64encode(buf.read()).decode('utf-8')
                    buf.close()
                    plt.close(fig)

            # 2. Company Talons Count Bar Chart
            ste_names = [x['ste_name'] for x in values.get('ste_summary', [])]
            ste_counts = [x['count_total'] for x in values.get('ste_summary', [])]
            
            if ste_names and sum(ste_counts) > 0:
                fig, ax = plt.subplots(figsize=(6, 4.5), dpi=120)
                bars = ax.bar(ste_names, ste_counts, color='#2980B9', width=0.5)
                
                # Add counts on top of bars
                for bar in bars:
                    height = bar.get_height()
                    ax.annotate(f'{int(height)}',
                                xy=(bar.get_x() + bar.get_width() / 2, height),
                                xytext=(0, 3),  # 3 points vertical offset
                                textcoords="offset points",
                                ha='center', va='bottom', fontsize=8, weight='bold')
                
                ax.set_ylabel("Nombre de Talons", fontsize=9, fontweight='bold')
                ax.set_title("Nombre de Talons par Société", fontsize=10, fontweight='bold', color='#1A4D80', pad=10)
                plt.xticks(rotation=15, ha='right', fontsize=8)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                fig.tight_layout()

                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight', transparent=True)
                buf.seek(0)
                charts_b64['company_bar'] = base64.b64encode(buf.read()).decode('utf-8')
                buf.close()
                plt.close(fig)
                
        except Exception as e:
            _logger.error("Error generating global talons charts: %s", str(e), exc_info=True)

        return charts_b64

    @api.model
    def generate_excel_data(self, values):
        try:
            import xlsxwriter
        except ImportError:
            return None
            
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Formats and Styles
        title_style = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#1A4D80', 'font_color': 'white'
        })
        date_box_style = workbook.add_format({
            'bold': True, 'font_size': 11, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#E2ECF7', 'font_color': '#1A4D80', 'border': 1, 'border_color': '#1A4D80'
        })
        sum_header_style = workbook.add_format({
            'bold': True, 'border': 1, 'border_color': '#B0CBE3', 'align': 'center',
            'bg_color': '#E2ECF7', 'font_color': '#1A4D80', 'font_size': 11
        })
        
        # State colors/styles
        style_coffre = workbook.add_format({'bg_color': '#E8F0FE', 'font_color': '#1A73E8', 'border': 1, 'border_color': '#B0CBE3', 'align': 'center'})
        style_actif = workbook.add_format({'bg_color': '#E6F4EA', 'font_color': '#137333', 'border': 1, 'border_color': '#B0CBE3', 'align': 'center'})
        style_cloture = workbook.add_format({'bg_color': '#FCE8E6', 'font_color': '#C5221F', 'border': 1, 'border_color': '#B0CBE3', 'align': 'center'})
        
        # Basic cells
        cell_center = workbook.add_format({'border': 1, 'border_color': '#B0CBE3', 'align': 'center'})
        cell_left = workbook.add_format({'border': 1, 'border_color': '#B0CBE3', 'align': 'left'})
        cell_left_bold = workbook.add_format({'bold': True, 'border': 1, 'border_color': '#B0CBE3', 'align': 'left', 'font_color': '#1A4D80'})
        cell_percent = workbook.add_format({'border': 1, 'border_color': '#B0CBE3', 'align': 'center', 'num_format': '0.0"%"'})
        
        # Theme specific for company header
        ste_header_style = workbook.add_format({
            'bold': True, 'font_size': 12, 'font_color': '#1A4D80', 'bg_color': '#F1F3F4',
            'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color': '#B0CBE3'
        })
        
        # Sheets creation
        sheet = workbook.add_worksheet("Synthese")
        sheet_details = workbook.add_worksheet("Details_Talons")
        
        sheet.set_default_row(20)
        sheet_details.set_default_row(20)
        
        sheet.set_column(0, 0, 20)  # Indicateur
        sheet.set_column(1, 1, 15)  # Valeur
        sheet.set_column(2, 2, 5)   # Spacing
        sheet.set_column(3, 3, 20)  # Société
        sheet.set_column(4, 4, 15)  # Total Talons
        sheet.set_column(5, 5, 15)  # Coffre
        sheet.set_column(6, 6, 15)  # Actifs
        sheet.set_column(7, 7, 15)  # Cloturés
        
        sheet_details.set_column(0, 0, 25)  # Société
        sheet_details.set_column(1, 1, 20)  # Talon
        sheet_details.set_column(2, 2, 12)  # Série
        sheet_details.set_column(3, 3, 12)  # Total Chqs
        sheet_details.set_column(4, 4, 12)  # Utilisés
        sheet_details.set_column(5, 5, 12)  # Restants
        sheet_details.set_column(6, 6, 12)  # Absents
        sheet_details.set_column(7, 7, 12)  # % Usage
        sheet_details.set_column(8, 8, 15)  # État
        sheet_details.set_column(9, 9, 20)  # Dernier Utilisé
        
        # --- TAB 1: SYNTHESE ---
        sheet.set_row(0, 30)
        sheet.write('A1', values['report_date'], date_box_style)
        sheet.merge_range('B1:H1', f"Rapport Global des Talons ({values['state_label_fr']})", title_style)
        
        # General metrics
        row = 3
        sheet.merge_range(row, 0, row, 1, "STATISTIQUES GENERALES", sum_header_style)
        row += 1
        
        metrics = [
            ("Total Talons", values['total_talons_count']),
            ("Talons en Coffre", values['total_coffre_count']),
            ("Talons Actifs", values['total_actif_count']),
            ("Talons Cloturés", values['total_cloture_count']),
            ("Total Chèques", values['total_chqs_count']),
            ("Chèques Utilisés", values['total_used_chqs']),
            ("Chèques Restants", values['total_unused_chqs']),
            ("Chèques Absents", values['total_missing_chqs']),
        ]
        
        for name, val in metrics:
            sheet.write(row, 0, name, cell_left_bold)
            sheet.write_number(row, 1, val, cell_center)
            row += 1
            
        sheet.write(row, 0, "Taux d'utilisation moyen", cell_left_bold)
        sheet.write_number(row, 1, values['avg_usage_percentage'] / 100.0, workbook.add_format({'bold': True, 'border': 1, 'border_color': '#B0CBE3', 'align': 'center', 'num_format': '0.0%'}))
        
        # Company Recap on the right
        comp_row = 3
        sheet.merge_range(comp_row, 3, comp_row, 7, "SYNTHESE PAR SOCIETE", sum_header_style)
        comp_row += 1
        
        sheet.write(comp_row, 3, "Société", sum_header_style)
        sheet.write(comp_row, 4, "Total Talons", sum_header_style)
        sheet.write(comp_row, 5, "Coffre", sum_header_style)
        sheet.write(comp_row, 6, "Actifs", sum_header_style)
        sheet.write(comp_row, 7, "Cloturés", sum_header_style)
        comp_row += 1
        
        for ste_info in values['ste_summary']:
            sheet.write(comp_row, 3, ste_info['ste_name'], cell_left_bold)
            sheet.write_number(comp_row, 4, ste_info['count_total'], cell_center)
            sheet.write_number(comp_row, 5, ste_info['count_coffre'], cell_center)
            sheet.write_number(comp_row, 6, ste_info['count_actif'], cell_center)
            sheet.write_number(comp_row, 7, ste_info['count_cloture'], cell_center)
            comp_row += 1
            
        # Add a nice state pie chart using excel native chart capabilities
        chart_state = workbook.add_chart({'type': 'pie'})
        chart_state.add_series({
            'categories': "='Synthese'!$A$5:$A$7",
            'values': "='Synthese'!$B$5:$B$7",
            'name': 'Répartition des Talons',
            'data_labels': {'percentage': True}
        })
        chart_state.set_title({
            'name': 'Répartition des Talons par État',
            'name_font': {'bold': True, 'size': 12, 'color': '#1A4D80'}
        })
        chart_state.set_size({'width': 350, 'height': 240})
        sheet.insert_chart('D16', chart_state)
        
        # --- TAB 2: DETAILS TALONS ---
        sheet_details.set_row(0, 30)
        sheet_details.merge_range('A1:J1', f"Détails des Talons ({values['state_label_fr']})", title_style)
        
        det_row = 2
        headers_details = [
            "Société", "Nom Talon", "Série", "Total Chqs", "Utilisés", 
            "Restants", "Absents", "% Usage", "État", "Dernier Utilisé"
        ]
        
        for col, h in enumerate(headers_details):
            sheet_details.write(det_row, col, h, sum_header_style)
        det_row += 1
        
        for ste_info in values['ste_summary']:
            # We can print a header row for each company
            sheet_details.merge_range(det_row, 0, det_row, 9, f"🏢 {ste_info['ste_name']}", ste_header_style)
            det_row += 1
            
            for t in ste_info['talons']:
                sheet_details.write(det_row, 0, ste_info['ste_name'], cell_left)
                sheet_details.write(det_row, 1, t['name_shown'], cell_left_bold)
                sheet_details.write(det_row, 2, t['serie'], cell_center)
                sheet_details.write_number(det_row, 3, t['total'], cell_center)
                sheet_details.write_number(det_row, 4, t['used'], cell_center)
                sheet_details.write_number(det_row, 5, t['remaining'], cell_center)
                sheet_details.write_number(det_row, 6, t['missing'], cell_center)
                sheet_details.write_number(det_row, 7, t['percentage'] / 100.0, cell_percent)
                
                # State styling
                if t['etat'] == 'coffre':
                    sheet_details.write(det_row, 8, t['state_label'], style_coffre)
                elif t['etat'] == 'actif':
                    sheet_details.write(det_row, 8, t['state_label'], style_actif)
                else:
                    sheet_details.write(det_row, 8, t['state_label'], style_cloture)
                    
                sheet_details.write(det_row, 9, t['last_used'], cell_center)
                det_row += 1
            
            # Subtotal per company
            sheet_details.write(det_row, 0, f"TOTAL {ste_info['ste_name']}", workbook.add_format({'bold': True, 'border': 1, 'border_color': '#B0CBE3', 'bg_color': '#FAFAFA'}))
            sheet_details.write(det_row, 1, f"{ste_info['count_total']} Talons", workbook.add_format({'bold': True, 'border': 1, 'border_color': '#B0CBE3', 'align': 'center'}))
            sheet_details.write(det_row, 2, "", cell_center)
            sheet_details.write_number(det_row, 3, ste_info['total_chqs'], workbook.add_format({'bold': True, 'border': 1, 'border_color': '#B0CBE3', 'align': 'center'}))
            sheet_details.write_number(det_row, 4, ste_info['used_chqs'], workbook.add_format({'bold': True, 'border': 1, 'border_color': '#B0CBE3', 'align': 'center'}))
            sheet_details.write_number(det_row, 5, ste_info['unused_chqs'], workbook.add_format({'bold': True, 'border': 1, 'border_color': '#B0CBE3', 'align': 'center'}))
            sheet_details.write_number(det_row, 6, ste_info['missing_chqs'], workbook.add_format({'bold': True, 'border': 1, 'border_color': '#B0CBE3', 'align': 'center'}))
            
            ste_avg = (ste_info['used_chqs'] / ste_info['total_chqs'] * 100) if ste_info['total_chqs'] else 0.0
            sheet_details.write_number(det_row, 7, ste_avg / 100.0, workbook.add_format({'bold': True, 'border': 1, 'border_color': '#B0CBE3', 'align': 'center', 'num_format': '0.0%'}))
            sheet_details.write(det_row, 8, "", cell_center)
            sheet_details.write(det_row, 9, "", cell_center)
            det_row += 2  # extra spacing
            
        workbook.close()
        output.seek(0)
        xlsx_base64 = base64.b64encode(output.read()).decode('utf-8')
        output.close()
        return xlsx_base64
