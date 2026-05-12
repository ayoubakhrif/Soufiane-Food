from odoo import models, fields, api

class ReportFinanceSituation(models.AbstractModel):
    _name = 'report.finance.report_finance_situation_template'
    _description = 'Rapport de Situation des Chèques Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Fetch physical cheques instead of datacheques (répartitions)
        domain = []
        if data and data.get('encours_only'):
            domain = [('encours', '=', 'non_encaisse')]
        physical_recs = self.env['finance.cheque.physical'].sudo().search(domain)
        
        active_list_phys = []
        reserve_list_phys = []
        bureau_list_phys = []
        annule_list_phys = []
        
        for physical in physical_recs:
            if not physical.datacheque_ids:
                continue
            first_datacheque = physical.datacheque_ids[0]
            state = first_datacheque.state or 'reserve'

            # Exclude Bureau and Annulé from outstanding (encours) analysis
            if data and data.get('encours_only') and state in ['bureau', 'annule']:
                continue

            type_selection = {
                'magasinage': 'Magasinage',
                'surestarie': 'Surestarie',
                'change': 'Change',
                'fret': 'Fret',
                'divers': 'Divers',
                'reserve': 'Réserve',
                'bureau': 'Bureau',
                'annule': 'Annulé'
            }
            type_label = type_selection.get(first_datacheque.type, 'Divers')

            item = {
                'chq': physical.name,
                'ste': physical.ste_id.name or 'Inconnu',
                'perso': first_datacheque.perso_id.name or 'Inconnu',
                'benif': physical.benif_id.name or 'Inconnu',
                'amount': physical.amount_total or 0.0,
                'date_emission': physical.date_emission,
                'date_echeance': physical.date_echeance,
                'type': type_label,
            }
            
            if state == 'actif':
                active_list_phys.append(item)
            elif state == 'reserve':
                reserve_list_phys.append(item)
            elif state == 'bureau':
                bureau_list_phys.append(item)
            elif state == 'annule':
                annule_list_phys.append(item)

        by_benif = data and data.get('by_benif')

        # 1. Active checks general recap (grouped by company or beneficiary)
        ste_summary = {}
        for item in active_list_phys:
            group_key = item['benif'] if by_benif else item['ste']
            if group_key not in ste_summary:
                ste_summary[group_key] = {
                    'ste_name': group_key, # for backward-compatibility with XML
                    'group_name': group_key,
                    'count': 0,
                    'total_amount': 0.0
                }
            ste_summary[group_key]['count'] += 1
            ste_summary[group_key]['total_amount'] += item['amount']

        ste_summary_list = list(ste_summary.values())
        ste_summary_list.sort(key=lambda x: -x['total_amount'])

        total_active_count = len(active_list_phys)
        total_active_amount = sum(item['amount'] for item in active_list_phys)

        # 2. Detailed Reserve Checks (sorted by company, then check number ascending)
        reserve_list_phys.sort(key=lambda x: (x['ste'].lower(), x['chq'] or ''))
        total_reserve_count = len(reserve_list_phys)
        total_reserve_amount = sum(item['amount'] for item in reserve_list_phys)

        # 3. Detailed Bureau Checks (sorted by company, then check number ascending)
        bureau_list_phys.sort(key=lambda x: (x['ste'].lower(), x['chq'] or ''))
        total_bureau_count = len(bureau_list_phys)
        total_bureau_amount = sum(item['amount'] for item in bureau_list_phys)

        # 4. Detailed Annulé Checks (sorted by company, then check number ascending)
        annule_list_phys.sort(key=lambda x: (x['ste'].lower(), x['chq'] or ''))
        total_annule_count = len(annule_list_phys)
        total_annule_amount = sum(item['amount'] for item in annule_list_phys)

        # Overall summary stats
        global_count = total_active_count + total_reserve_count + total_bureau_count + total_annule_count
        global_amount = total_active_amount + total_reserve_amount + total_bureau_amount + total_annule_amount

        res = {
            'doc_ids': docids,
            'doc_model': 'finance.cheque.physical',
            'active_list': active_list_phys,
            'active_summary': ste_summary_list,
            'total_active_count': total_active_count,
            'total_active_amount': total_active_amount,
            
            'reserve_list': reserve_list_phys,
            'total_reserve_count': total_reserve_count,
            'total_reserve_amount': total_reserve_amount,
            
            'bureau_list': bureau_list_phys,
            'total_bureau_count': total_bureau_count,
            'total_bureau_amount': total_bureau_amount,
            
            'annule_list': annule_list_phys,
            'total_annule_count': total_annule_count,
            'total_annule_amount': total_annule_amount,
            
            'global_count': global_count,
            'global_amount': global_amount,
            
            'by_benif': by_benif,
            'report_date': fields.Date.today().strftime('%d/%m/%Y'),
            'report_title': (
                ("Situation des Chèques En Cours par Bénéficiaire" if (data and data.get('encours_only')) else "Situation Générale des Chèques par Bénéficiaire")
                if by_benif else
                ("Situation des Chèques En Cours" if (data and data.get('encours_only')) else "Situation Générale des Chèques")
            ),
        }

        # Generate base64 charts for the QWeb PDF
        res['charts'] = self._generate_base64_charts(res)
        return res

    def _generate_base64_charts(self, values):
        charts_b64 = {
            'company_pie': '',
            'state_pie': ''
        }

        try:
            import matplotlib
            try:
                matplotlib.use('Agg')
            except Exception:
                pass
            import matplotlib.pyplot as plt
            import io
                     # 1. Company / Beneficiary Pie Chart
            by_benif = values.get('by_benif')
            comp_totals = {}
            for lst_key in ['active_list', 'reserve_list', 'bureau_list', 'annule_list']:
                for chq in values.get(lst_key, []):
                    group_key = chq.get('benif', 'Inconnu') if by_benif else chq.get('ste', 'Inconnu')
                    comp_totals[group_key] = comp_totals.get(group_key, 0.0) + chq.get('amount', 0.0)
            
            if comp_totals:
                sorted_comps = sorted(comp_totals.items(), key=lambda x: -x[1])
                labels = [x[0] for x in sorted_comps]
                amounts = [x[1] for x in sorted_comps]
                
                colors = ['#1A4D80', '#2980B9', '#3498DB', '#5DADE2', '#85C1E9', '#A9CCE3', '#D4E6F1']
                if len(labels) > len(colors):
                    colors = colors * (len(labels) // len(colors) + 1)
                colors = colors[:len(labels)]
 
                fig, ax = plt.subplots(figsize=(5, 4.5), dpi=120)
                wedges, texts, autotexts = ax.pie(
                    amounts, 
                    labels=labels, 
                    autopct='%1.1f%%',
                    startangle=140, 
                    colors=colors,
                    textprops=dict(color="black", fontsize=8)
                )
                plt.setp(autotexts, size=8, weight="bold")
                title_lbl = "Répartition Financière par Bénéficiaire" if by_benif else "Répartition Financière par Société"
                ax.set_title(title_lbl, fontsize=10, fontweight='bold', color='#1A4D80', pad=10)
                fig.tight_layout()

                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight', transparent=True)
                buf.seek(0)
                charts_b64['company_pie'] = base64.b64encode(buf.read()).decode('utf-8')
                buf.close()
                plt.close(fig)

            # 2. State Pie Chart
            state_counts = {
                'ACTIF': len(values.get('active_list', [])),
                'RÉSERVE': len(values.get('reserve_list', [])),
                'BUREAU': len(values.get('bureau_list', [])),
                'ANNULÉ': len(values.get('annule_list', []))
            }
            state_counts = {k: v for k, v in state_counts.items() if v > 0}
            if state_counts:
                labels = list(state_counts.keys())
                counts = list(state_counts.values())
                
                state_colors = {
                    'ACTIF': '#137333',
                    'RÉSERVE': '#1A73E8',
                    'BUREAU': '#E67E22',
                    'ANNULÉ': '#D93025'
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
                ax.set_title("Répartition Globale par Nombre de Chèques", fontsize=10, fontweight='bold', color='#1A4D80', pad=10)
                fig.tight_layout()

                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight', transparent=True)
                buf.seek(0)
                charts_b64['state_pie'] = base64.b64encode(buf.read()).decode('utf-8')
                buf.close()
                plt.close(fig)
        except Exception as e:
            import logging
            logging.getLogger('odoo.addons.finance').error("ERREUR DE GENERATION DE GRAPHIQUES PDF: %s", str(e), exc_info=True)

        return charts_b64

    @api.model
    def generate_excel_data(self, values):
        import io
        import base64
        try:
            import xlsxwriter
        except ImportError:
            return None
            
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Define formats/styles
        title_style = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#1A4D80', 'font_color': 'white'
        })
        date_box_style = workbook.add_format({
            'bold': True, 'font_size': 12, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#E2ECF7', 'font_color': '#1A4D80', 'border': 1, 'border_color': '#1A4D80'
        })
        
        # Summary Styles
        sum_header_style = workbook.add_format({
            'bold': True, 'border': 1, 'border_color': '#B0CBE3', 'align': 'center',
            'bg_color': '#E2ECF7', 'font_color': '#1A4D80', 'font_size': 11
        })
        
        sum_row_actif = workbook.add_format({'bg_color': '#E6F4EA', 'font_color': '#137333', 'border': 1, 'border_color': '#B0CBE3', 'align': 'center'})
        sum_row_actif_amt = workbook.add_format({'bg_color': '#E6F4EA', 'font_color': '#137333', 'border': 1, 'border_color': '#B0CBE3', 'align': 'right', 'num_format': '#,##0.00" DH"'})
        
        sum_row_reserve = workbook.add_format({'bg_color': '#FEF7E0', 'font_color': '#B06000', 'border': 1, 'border_color': '#B0CBE3', 'align': 'center'})
        sum_row_reserve_amt = workbook.add_format({'bg_color': '#FEF7E0', 'font_color': '#B06000', 'border': 1, 'border_color': '#B0CBE3', 'align': 'right', 'num_format': '#,##0.00" DH"'})
        
        sum_row_bureau = workbook.add_format({'bg_color': '#E8F0FE', 'font_color': '#1A73E8', 'border': 1, 'border_color': '#B0CBE3', 'align': 'center'})
        sum_row_bureau_amt = workbook.add_format({'bg_color': '#E8F0FE', 'font_color': '#1A73E8', 'border': 1, 'border_color': '#B0CBE3', 'align': 'right', 'num_format': '#,##0.00" DH"'})
        
        sum_row_annule = workbook.add_format({'bg_color': '#FCE8E6', 'font_color': '#C5221F', 'border': 1, 'border_color': '#B0CBE3', 'align': 'center'})
        sum_row_annule_amt = workbook.add_format({'bg_color': '#FCE8E6', 'font_color': '#C5221F', 'border': 1, 'border_color': '#B0CBE3', 'align': 'right', 'num_format': '#,##0.00" DH"'})
        
        sum_row_global = workbook.add_format({'bold': True, 'bg_color': '#F1F3F4', 'font_color': '#3C4043', 'border': 1, 'border_color': '#B0CBE3', 'align': 'center', 'font_size': 12})
        sum_row_global_amt = workbook.add_format({'bold': True, 'bg_color': '#F1F3F4', 'font_color': '#3C4043', 'border': 1, 'border_color': '#B0CBE3', 'align': 'right', 'num_format': '#,##0.00" DH"', 'font_size': 12})
        
        # State Specific Section formats
        # Theme colors: Green (#137333, #E6F4EA), Orange (#B06000, #FEF7E0), Blue (#1A73E8, #E8F0FE), Red (#C5221F, #FCE8E6)
        
        def make_theme_formats(hdr_color, row_color, txt_color):
            section_title = workbook.add_format({'bold': True, 'font_size': 12, 'font_color': txt_color, 'align': 'left', 'valign': 'vcenter'})
            header = workbook.add_format({'bold': True, 'border': 1, 'border_color': hdr_color, 'align': 'center', 'bg_color': hdr_color, 'font_color': 'white'})
            cell_center = workbook.add_format({'border': 1, 'border_color': row_color, 'align': 'center'})
            cell_left = workbook.add_format({'border': 1, 'border_color': row_color, 'align': 'left'})
            cell_left_bold = workbook.add_format({'bold': True, 'border': 1, 'border_color': row_color, 'align': 'left', 'font_color': txt_color})
            cell_money = workbook.add_format({'bold': True, 'border': 1, 'border_color': row_color, 'align': 'right', 'font_color': txt_color, 'num_format': '#,##0.00" DH"'})
            cell_date = workbook.add_format({'border': 1, 'border_color': row_color, 'align': 'center', 'num_format': 'dd/mm/yyyy'})
            total_cell = workbook.add_format({'bold': True, 'bg_color': row_color, 'font_color': txt_color, 'border': 1, 'border_color': hdr_color, 'align': 'center'})
            total_cell_left = workbook.add_format({'bold': True, 'bg_color': row_color, 'font_color': txt_color, 'border': 1, 'border_color': hdr_color, 'align': 'left'})
            total_cell_money = workbook.add_format({'bold': True, 'bg_color': row_color, 'font_color': txt_color, 'border': 1, 'border_color': hdr_color, 'align': 'right', 'num_format': '#,##0.00" DH"'})
            empty_cell = workbook.add_format({'italic': True, 'border': 1, 'border_color': row_color, 'align': 'center', 'font_color': '#666666'})
            return {
                'title': section_title, 'header': header, 'center': cell_center, 'left': cell_left, 'left_bold': cell_left_bold,
                'money': cell_money, 'date': cell_date, 'total': total_cell, 'total_left': total_cell_left, 'total_money': total_cell_money, 'empty': empty_cell
            }
            
        themes = {
            'actif': make_theme_formats('#137333', '#E6F4EA', '#137333'),
            'reserve': make_theme_formats('#B06000', '#FEF7E0', '#B06000'),
            'bureau': make_theme_formats('#1A73E8', '#E8F0FE', '#1A73E8'),
            'annule': make_theme_formats('#C5221F', '#FCE8E6', '#C5221F'),
        }

        sheet_analysis = workbook.add_worksheet("Analyses")
        sheet = workbook.add_worksheet("Situation_Cheques")
        sheet_analysis.activate()
        
        sheet.set_default_row(20)
        sheet_analysis.set_default_row(20)
        
        # Set column widths for Data sheet
        sheet.set_column(0, 0, 15)  # N° Chèque / Société
        sheet.set_column(1, 1, 28)  # Société / Nbre Chqs
        sheet.set_column(2, 2, 28)  # Bénéficiaire / Montant
        sheet.set_column(3, 3, 20)  # Personne
        sheet.set_column(4, 4, 15)  # Échéance
        sheet.set_column(5, 5, 18)  # Montant
        
        # Set column widths for Analysis sheet
        sheet_analysis.set_column(0, 5, 18)

        # Header Block on Data Sheet
        sheet.set_row(0, 30)
        sheet.write('A1', values['report_date'], date_box_style)
        sheet.merge_range('B1:F1', "Situation Générale des Chèques", title_style)
        
        # Dashboard Title
        sheet_analysis.merge_range('A1:F1', "TABLEAU DE BORD D'ANALYSE", title_style)
        
        row = 2
        
        # Summary table (Data Sheet)
        sheet.write(row, 0, "État", sum_header_style)
        sheet.write(row, 1, "Nombre de Chèques", sum_header_style)
        sheet.write(row, 2, "Montant Global", sum_header_style)
        row += 1
        
        # Actif
        sheet.write(row, 0, "ACTIFS", sum_row_actif)
        sheet.write_number(row, 1, values['total_active_count'], sum_row_actif)
        sheet.write_number(row, 2, values['total_active_amount'], sum_row_actif_amt)
        row += 1
        # Reserve
        sheet.write(row, 0, "RÉSERVE", sum_row_reserve)
        sheet.write_number(row, 1, values['total_reserve_count'], sum_row_reserve)
        sheet.write_number(row, 2, values['total_reserve_amount'], sum_row_reserve_amt)
        row += 1
        # Bureau
        sheet.write(row, 0, "BUREAU", sum_row_bureau)
        sheet.write_number(row, 1, values['total_bureau_count'], sum_row_bureau)
        sheet.write_number(row, 2, values['total_bureau_amount'], sum_row_bureau_amt)
        row += 1
        # Annule
        sheet.write(row, 0, "ANNULÉS", sum_row_annule)
        sheet.write_number(row, 1, values['total_annule_count'], sum_row_annule)
        sheet.write_number(row, 2, values['total_annule_amount'], sum_row_annule_amt)
        row += 1
        # Global Total
        sheet.write(row, 0, "TOTAL GENERAL", sum_row_global)
        sheet.write_number(row, 1, values['global_count'], sum_row_global)
        sheet.write_number(row, 2, values['global_amount'], sum_row_global_amt)

        # --- COMPANY SUMMARY TABLE (Columns D, E, F) ---
        company_stats = {}
        for lst_key in ['active_list', 'reserve_list', 'bureau_list', 'annule_list']:
            for chq in values.get(lst_key, []):
                ste = chq.get('ste', 'Inconnu')
                if ste not in company_stats:
                    company_stats[ste] = {'ste_name': ste, 'count': 0, 'total_amount': 0.0}
                company_stats[ste]['count'] += 1
                company_stats[ste]['total_amount'] += chq['amount']
        
        sorted_company_stats = sorted(list(company_stats.values()), key=lambda x: -x['total_amount'])
        
        comp_sum_row = 2
        sheet.write(comp_sum_row, 3, "Société", sum_header_style)
        sheet.write(comp_sum_row, 4, "Nombre de Chèques", sum_header_style)
        sheet.write(comp_sum_row, 5, "Montant Global", sum_header_style)
        comp_sum_row += 1
        
        start_row_comp_sum_excel = comp_sum_row + 1
        
        sum_row_comp = workbook.add_format({'border': 1, 'border_color': '#B0CBE3', 'align': 'center'})
        sum_row_comp_left = workbook.add_format({'bold': True, 'border': 1, 'border_color': '#B0CBE3', 'align': 'left', 'font_color': '#1A4D80'})
        sum_row_comp_amt = workbook.add_format({'border': 1, 'border_color': '#B0CBE3', 'align': 'right', 'num_format': '#,##0.00" DH"'})
        
        for c_stat in sorted_company_stats:
            sheet.write(comp_sum_row, 3, c_stat['ste_name'], sum_row_comp_left)
            sheet.write_number(comp_sum_row, 4, c_stat['count'], sum_row_comp)
            sheet.write_number(comp_sum_row, 5, c_stat['total_amount'], sum_row_comp_amt)
            comp_sum_row += 1
            
        end_row_comp_sum_excel = comp_sum_row
        # -----------------------------------------------
        
        row += 2  # spacing
        
        # 1. SECTION ACTIFS (RECAP GENERAL)
        t_actif = themes['actif']
        sheet.merge_range(row, 0, row, 2, "Récapitulatif des Chèques Actifs", t_actif['title'])
        row += 1
        
        sheet.write(row, 0, "Société (Émettrice)", t_actif['header'])
        sheet.write(row, 1, "Nombre de Chèques", t_actif['header'])
        sheet.write(row, 2, "Montant Total", t_actif['header'])
        row += 1
        
        start_row_active_excel = row + 1
        if values['active_summary']:
            for active in values['active_summary']:
                sheet.write(row, 0, active['ste_name'], t_actif['left_bold'])
                sheet.write_number(row, 1, active['count'], t_actif['center'])
                sheet.write_number(row, 2, active['total_amount'], t_actif['money'])
                row += 1
        else:
            sheet.merge_range(row, 0, row, 2, "Aucun chèque actif trouvé.", t_actif['empty'])
            row += 1
        end_row_active_excel = row
            
        sheet.write(row, 0, "TOTAL ACTIFS", t_actif['total_left'])
        sheet.write_number(row, 1, values['total_active_count'], t_actif['total'])
        sheet.write_number(row, 2, values['total_active_amount'], t_actif['total_money'])
        row += 2  # spacing
        
        # 2. SECTION RÉSERVE (DETAIL)
        t_res = themes['reserve']
        sheet.merge_range(row, 0, row, 5, "Détail des Chèques en Réserve", t_res['title'])
        row += 1
        
        headers_res = ["N° Chèque", "Société", "Bénéficiaire", "Personne", "Échéance", "Montant"]
        for col, h in enumerate(headers_res):
            sheet.write(row, col, h, t_res['header'])
        row += 1
        
        if values['reserve_list']:
            from datetime import datetime, time
            for item in values['reserve_list']:
                sheet.write(row, 0, item['chq'] or "", t_res['center'])
                sheet.write(row, 1, item['ste'], t_res['left_bold'])
                sheet.write(row, 2, item['benif'], t_res['left'])
                sheet.write(row, 3, item['perso'], t_res['left'])
                
                # Format date for xlsxwriter
                d_ech = item['date_echeance']
                if d_ech:
                    sheet.write_datetime(row, 4, datetime.combine(d_ech, time.min), t_res['date'])
                else:
                    sheet.write(row, 4, "", t_res['center'])
                    
                sheet.write_number(row, 5, item['amount'], t_res['money'])
                row += 1
        else:
            sheet.merge_range(row, 0, row, 5, "Aucun chèque en réserve.", t_res['empty'])
            row += 1
            
        if values['reserve_list']:
            sheet.merge_range(row, 0, row, 4, "TOTAL RÉSERVE", t_res['total_left'])
            sheet.write_number(row, 5, values['total_reserve_amount'], t_res['total_money'])
            row += 2  # spacing
        else:
            row += 1
            
        # 3. SECTION BUREAU (DETAIL)
        t_bur = themes['bureau']
        sheet.merge_range(row, 0, row, 4, "Détail des Chèques Bureau", t_bur['title'])
        row += 1
        
        headers_bur = ["N° Chèque", "Société", "Bénéficiaire", "Personne", "Montant"]
        for col, h in enumerate(headers_bur):
            sheet.write(row, col, h, t_bur['header'])
        row += 1
        
        if values['bureau_list']:
            for item in values['bureau_list']:
                sheet.write(row, 0, item['chq'] or "", t_bur['center'])
                sheet.write(row, 1, item['ste'], t_bur['left_bold'])
                sheet.write(row, 2, item['benif'], t_bur['left'])
                sheet.write(row, 3, item['perso'], t_bur['left'])
                sheet.write_number(row, 4, item['amount'], t_bur['money'])
                row += 1
        else:
            sheet.merge_range(row, 0, row, 4, "Aucun chèque bureau.", t_bur['empty'])
            row += 1
            
        if values['bureau_list']:
            sheet.merge_range(row, 0, row, 3, "TOTAL BUREAU", t_bur['total_left'])
            sheet.write_number(row, 4, values['total_bureau_amount'], t_bur['total_money'])
            row += 2  # spacing
        else:
            row += 1
            
        # 4. SECTION ANNULÉ (DETAIL)
        t_ann = themes['annule']
        sheet.merge_range(row, 0, row, 4, "Détail des Chèques Annulés", t_ann['title'])
        row += 1
        
        for col, h in enumerate(headers_bur):
            sheet.write(row, col, h, t_ann['header'])
        row += 1
        
        if values['annule_list']:
            for item in values['annule_list']:
                sheet.write(row, 0, item['chq'] or "", t_ann['center'])
                sheet.write(row, 1, item['ste'], t_ann['left_bold'])
                sheet.write(row, 2, item['benif'], t_ann['left'])
                sheet.write(row, 3, item['perso'], t_ann['left'])
                sheet.write_number(row, 4, item['amount'], t_ann['money'])
                row += 1
        else:
            sheet.merge_range(row, 0, row, 4, "Aucun chèque annulé.", t_ann['empty'])
            row += 1
            
        if values['annule_list']:
            sheet.merge_range(row, 0, row, 3, "TOTAL ANNULÉS", t_ann['total_left'])
            sheet.write_number(row, 4, values['total_annule_amount'], t_ann['total_money'])
            row += 1

        by_benif = values.get('by_benif')

        # Chart 1: Pie Chart for Group Distribution by Amount
        chart_state = workbook.add_chart({'type': 'pie'})
        chart_state.add_series({
            'categories': f"='Situation_Cheques'!$D$4:$D${end_row_comp_sum_excel}",
            'values': f"='Situation_Cheques'!$F$4:$F${end_row_comp_sum_excel}",
            'name': 'Part Financière par Bénéficiaire' if by_benif else 'Part Financière par Société',
            'data_labels': {'percentage': True}
        })
        chart_state.set_title({
            'name': 'Répartition Financière par Bénéficiaire' if by_benif else 'Répartition Financière par Société',
            'name_font': {'bold': True, 'size': 12, 'color': '#1A4D80'}
        })
        chart_state.set_size({'width': 380, 'height': 260})
        sheet_analysis.insert_chart('B3', chart_state)

        # Chart 3: Pie Chart for Group Distribution by Check Count
        chart_count = workbook.add_chart({'type': 'pie'})
        chart_count.add_series({
            'categories': f"='Situation_Cheques'!$D$4:$D${end_row_comp_sum_excel}",
            'values': f"='Situation_Cheques'!$E$4:$E${end_row_comp_sum_excel}",
            'name': 'Nombre de Chèques par Bénéficiaire' if by_benif else 'Nombre de Chèques par Société',
            'data_labels': {'percentage': True}
        })
        chart_count.set_title({
            'name': 'Répartition par Nombre de Chèques par Bénéficiaire' if by_benif else 'Répartition par Nombre de Chèques par Société',
            'name_font': {'bold': True, 'size': 12, 'color': '#1A4D80'}
        })
        chart_count.set_size({'width': 380, 'height': 260})
        sheet_analysis.insert_chart('E3', chart_count)

        # Chart 4: Pie Chart for States Distribution by Check Count
        chart_state_count = workbook.add_chart({'type': 'pie'})
        chart_state_count.add_series({
            'categories': "='Situation_Cheques'!$A$4:$A$7",
            'values': "='Situation_Cheques'!$B$4:$B$7",
            'name': 'Répartition des États',
            'data_labels': {'percentage': True}
        })
        chart_state_count.set_title({
            'name': 'Répartition des États par Nbre de Chèques',
            'name_font': {'bold': True, 'size': 12, 'color': '#1A4D80'}
        })
        chart_state_count.set_size({'width': 380, 'height': 260})
        sheet_analysis.insert_chart('I3', chart_state_count)

        # Chart 2: Column Chart for Active Checks per Group
        if values.get('active_summary') and start_row_active_excel <= end_row_active_excel:
            chart_active = workbook.add_chart({'type': 'column'})
            chart_active.add_series({
                'categories': f"='Situation_Cheques'!$A${start_row_active_excel}:$A${end_row_active_excel}",
                'values': f"='Situation_Cheques'!$C${start_row_active_excel}:$C${end_row_active_excel}",
                'name': 'Montant Total Actif (MAD)',
                'data_labels': {'value': True}
            })
            chart_active.set_title({
                'name': 'Encours Actif par Bénéficiaire' if by_benif else 'Encours Actif par Société',
                'name_font': {'bold': True, 'size': 14, 'color': '#137333'}
            })
            chart_active.set_x_axis({
                'name': 'Bénéficiaires' if by_benif else 'Sociétés Émettrices',
                'name_font': {'size': 10, 'bold': True}
            })
            chart_active.set_y_axis({
                'name': 'Montant Cumulé (MAD)',
                'name_font': {'size': 10, 'bold': True}
            })
            chart_active.set_legend({'none':        # ----------------------------------------------------
        # 6. DETAILED SHEETS PER GROUP (SOCIÉTÉ OR BÉNÉFICIAIRE)
        # ----------------------------------------------------
        all_groups = set()
        for lst_key in ['active_list', 'reserve_list', 'bureau_list', 'annule_list']:
            for chq in values.get(lst_key, []):
                val_key = chq.get('benif') if by_benif else chq.get('ste')
                if val_key:
                    all_groups.add(val_key)
        
        sorted_groups = sorted(list(all_groups))
        
        def make_safe_sheet_name(name):
            for char in [':', '\\', '/', '?', '*', '[', ']']:
                name = name.replace(char, '')
            return name[:30]  # Excel 31 characters limit

        from datetime import datetime, time

        for group_item in sorted_groups:
            safe_name = make_safe_sheet_name(group_item)
            sheet_company = workbook.add_worksheet(safe_name)
            sheet_company.set_default_row(20)
            
            # Column widths for detailed sheet
            sheet_company.set_column(0, 0, 15)  # État
            sheet_company.set_column(1, 1, 15)  # N° Chèque
            sheet_company.set_column(2, 2, 28)  # Société or Bénéficiaire
            sheet_company.set_column(3, 3, 20)  # Personne
            sheet_company.set_column(4, 4, 15)  # Échéance
            sheet_company.set_column(5, 5, 18)  # Montant
            
            # Title block
            title_text = f"Situation Détaillée — {group_item}"
            sheet_company.set_row(0, 30)
            sheet_company.merge_range('A1:F1', title_text, title_style)
            
            # Write Headers
            comp_row = 2
            sheet_company.write(comp_row, 0, "État", sum_header_style)
            sheet_company.write(comp_row, 1, "N° Chèque", sum_header_style)
            sheet_company.write(comp_row, 2, "Société" if by_benif else "Bénéficiaire", sum_header_style)
            sheet_company.write(comp_row, 3, "Personne", sum_header_style)
            sheet_company.write(comp_row, 4, "Échéance", sum_header_style)
            sheet_company.write(comp_row, 5, "Montant", sum_header_style)
            comp_row += 1
            
            # Gather and tag group-specific checks
            company_checks = []
            
            # Actifs
            for chq in values.get('active_list', []):
                match_val = chq['benif'] if by_benif else chq['ste']
                if match_val == group_item:
                    c_copy = chq.copy()
                    c_copy['state_label'] = 'ACTIF'
                    c_copy['theme'] = themes['actif']
                    company_checks.append(c_copy)
            
            # Réserve
            for chq in values.get('reserve_list', []):
                match_val = chq['benif'] if by_benif else chq['ste']
                if match_val == group_item:
                    c_copy = chq.copy()
                    c_copy['state_label'] = 'RÉSERVE'
                    c_copy['theme'] = themes['reserve']
                    company_checks.append(c_copy)
                    
            # Bureau
            for chq in values.get('bureau_list', []):
                match_val = chq['benif'] if by_benif else chq['ste']
                if match_val == group_item:
                    c_copy = chq.copy()
                    c_copy['state_label'] = 'BUREAU'
                    c_copy['theme'] = themes['bureau']
                    company_checks.append(c_copy)
                    
            # Annulé
            for chq in values.get('annule_list', []):
                match_val = chq['benif'] if by_benif else chq['ste']
                if match_val == group_item:
                    c_copy = chq.copy()
                    c_copy['state_label'] = 'ANNULÉ'
                    c_copy['theme'] = themes['annule']
                    company_checks.append(c_copy)
                    
            # Sort checks by State order, then check number
            state_priority = {'ACTIF': 0, 'RÉSERVE': 1, 'BUREAU': 2, 'ANNULÉ': 3}
            company_checks.sort(key=lambda x: (state_priority[x['state_label']], x['chq'] or ''))
            
            if company_checks:
                for c in company_checks:
                    t = c['theme']
                    sheet_company.write(comp_row, 0, c['state_label'], t['left_bold'])
                    sheet_company.write(comp_row, 1, c['chq'] or "", t['center'])
                    sheet_company.write(comp_row, 2, c['ste'] if by_benif else c['benif'], t['left'])
                    sheet_company.write(comp_row, 3, c['perso'], t['left'])
                    
                    d_ech = c['date_echeance']
                    if d_ech:
                        sheet_company.write_datetime(comp_row, 4, datetime.combine(d_ech, time.min), t['date'])
                    else:
                        sheet_company.write(comp_row, 4, "", t['center'])
                        
                    sheet_company.write_number(comp_row, 5, c['amount'], t['money'])
                    comp_row += 1
                
                # Write group total
                sheet_company.merge_range(comp_row, 0, comp_row, 4, f"TOTAL ENCOURS — {group_item}", sum_row_global)
                sheet_company.write_number(comp_row, 5, sum(c['amount'] for c in company_checks), sum_row_global_amt)

                # --- GROUP SUMMARY ANALYSES (Right Side) ---
                comp_state_stats = {
                    'ACTIF': {'count': 0, 'amount': 0.0},
                    'RÉSERVE': {'count': 0, 'amount': 0.0},
                    'BUREAU': {'count': 0, 'amount': 0.0},
                    'ANNULÉ': {'count': 0, 'amount': 0.0},
                }
                for c in company_checks:
                    lbl = c['state_label']
                    comp_state_stats[lbl]['count'] += 1
                    comp_state_stats[lbl]['amount'] += c['amount']
                
                sheet_company.set_column(6, 6, 3)   # Separator column
                sheet_company.set_column(7, 7, 12)  # Summary State
                sheet_company.set_column(8, 8, 12)  # Summary Count
                sheet_company.set_column(9, 9, 18)  # Summary Amount
                
                # Headers for the Right-Side Summary
                sheet_company.write(2, 7, "État", sum_header_style)
                sheet_company.write(2, 8, "Nombre", sum_header_style)
                sheet_company.write(2, 9, "Montant Global", sum_header_style)
                
                state_keys_ordered = ['ACTIF', 'RÉSERVE', 'BUREAU', 'ANNULÉ']
                state_theme_mapping = {
                    'ACTIF': themes['actif'],
                    'RÉSERVE': themes['reserve'],
                    'BUREAU': themes['bureau'],
                    'ANNULÉ': themes['annule']
                }
                
                for idx, state_lbl in enumerate(state_keys_ordered):
                    stat = comp_state_stats[state_lbl]
                    t_state = state_theme_mapping[state_lbl]
                    
                    sheet_company.write(3 + idx, 7, state_lbl, t_state['left_bold'])
                    sheet_company.write_number(3 + idx, 8, stat['count'], t_state['center'])
                    sheet_company.write_number(3 + idx, 9, stat['amount'], t_state['money'])
                    
                # Total for Right-Side Summary
                sheet_company.write(7, 7, "TOTAL", sum_row_global)
                sheet_company.write_number(7, 8, sum(s['count'] for s in comp_state_stats.values()), sum_row_global)
                sheet_company.write_number(7, 9, sum(s['amount'] for s in comp_state_stats.values()), sum_row_global_amt)
                
                # Pie Chart on the Right (Distribution by Check Counts in Percentage)
                chart_comp_state = workbook.add_chart({'type': 'pie'})
                chart_comp_state.add_series({
                    'categories': f"='{safe_name}'!$H$4:$H$7",
                    'values': f"='{safe_name}'!$I$4:$I$7",
                    'name': 'Répartition par État',
                    'data_labels': {'percentage': True}
                })
                chart_comp_state.set_title({
                    'name': 'Répartition par Nombre de Chèques',
                    'name_font': {'bold': True, 'size': 12, 'color': '#1A4D80'}
                })
                chart_comp_state.set_size({'width': 440, 'height': 280})
                sheet_company.insert_chart('L2', chart_comp_state)

                # --- TYPES SUMMARY (Right Side) ---
                comp_type_stats = {}
                for c in company_checks:
                    t_lbl = c.get('type') or 'Divers'
                    if t_lbl not in comp_type_stats:
                        comp_type_stats[t_lbl] = {'count': 0, 'amount': 0.0}
                    comp_type_stats[t_lbl]['count'] += 1
                    comp_type_stats[t_lbl]['amount'] += c['amount']
                
                # Headers for the Types Summary
                sheet_company.write(9, 7, "Type", sum_header_style)
                sheet_company.write(9, 8, "Nombre", sum_header_style)
                sheet_company.write(9, 9, "Montant Global", sum_header_style)
                
                type_row_curr = 10
                type_row_excel_start = type_row_curr + 1  # 1-based Excel row (11)
                
                sum_row_type_neutral = workbook.add_format({'border': 1, 'border_color': '#B0CBE3', 'align': 'center'})
                sum_row_type_neutral_left = workbook.add_format({'bold': True, 'border': 1, 'border_color': '#B0CBE3', 'align': 'left', 'font_color': '#1A4D80'})
                sum_row_type_neutral_amt = workbook.add_format({'border': 1, 'border_color': '#B0CBE3', 'align': 'right', 'num_format': '#,##0.00" DH"'})
                
                # Sort types by amount descending
                sorted_type_stats = sorted(list(comp_type_stats.items()), key=lambda x: -x[1]['amount'])
                
                for t_lbl, stat in sorted_type_stats:
                    sheet_company.write(type_row_curr, 7, t_lbl, sum_row_type_neutral_left)
                    sheet_company.write_number(type_row_curr, 8, stat['count'], sum_row_type_neutral)
                    sheet_company.write_number(type_row_curr, 9, stat['amount'], sum_row_type_neutral_amt)
                    type_row_curr += 1
                    
                type_row_excel_end = type_row_curr  # 1-based Excel row of last data row
                
                # Total for Types Summary
                sheet_company.write(type_row_curr, 7, "TOTAL", sum_row_global)
                sheet_company.write_number(type_row_curr, 8, sum(s['count'] for s in comp_type_stats.values()), sum_row_global)
                sheet_company.write_number(type_row_curr, 9, sum(s['amount'] for s in comp_type_stats.values()), sum_row_global_amt)

                # Second Pie Chart on the Right (Distribution of Types by Check Counts in Percentage)
                chart_comp_type = workbook.add_chart({'type': 'pie'})
                chart_comp_type.add_series({
                    'categories': f"='{safe_name}'!$H${type_row_excel_start}:$H${type_row_excel_end}",
                    'values': f"='{safe_name}'!$I${type_row_excel_start}:$I${type_row_excel_end}",
                    'name': 'Répartition par Type',
                    'data_labels': {'percentage': True}
                })
                chart_comp_type.set_title({
                    'name': 'Répartition par Type de Dossier',
                    'name_font': {'bold': True, 'size': 12, 'color': '#137333'}
                })
                chart_comp_type.set_size({'width': 440, 'height': 280})
                sheet_company.insert_chart('L18', chart_comp_type)

                # --- BENEFICIARY COMPANIES BREAKDOWN (Right Side, below Types Summary) ---
                if by_benif:
                    comp_breakdown_row = type_row_curr + 2
                    sheet_company.write(comp_breakdown_row, 7, "Société Émettrice", sum_header_style)
                    sheet_company.write(comp_breakdown_row, 8, "Nombre", sum_header_style)
                    sheet_company.write(comp_breakdown_row, 9, "Montant Global", sum_header_style)
                    comp_breakdown_row += 1
                    
                    benif_comp_stats = {}
                    for c in company_checks:
                        c_ste = c['ste']
                        if c_ste not in benif_comp_stats:
                            benif_comp_stats[c_ste] = {'count': 0, 'amount': 0.0}
                        benif_comp_stats[c_ste]['count'] += 1
                        benif_comp_stats[c_ste]['amount'] += c['amount']
                    
                    sorted_benif_comp = sorted(list(benif_comp_stats.items()), key=lambda x: -x[1]['amount'])
                    
                    for ste_lbl, stat in sorted_benif_comp:
                        sheet_company.write(comp_breakdown_row, 7, ste_lbl, sum_row_type_neutral_left)
                        sheet_company.write_number(comp_breakdown_row, 8, stat['count'], sum_row_type_neutral)
                        sheet_company.write_number(comp_breakdown_row, 9, stat['amount'], sum_row_type_neutral_amt)
                        comp_breakdown_row += 1
                    
                    # Total row for Company Breakdown
                    sheet_company.write(comp_breakdown_row, 7, "TOTAL S/SOCIÉTÉS", sum_row_global)
                    sheet_company.write_number(comp_breakdown_row, 8, sum(s['count'] for s in benif_comp_stats.values()), sum_row_global)
                    sheet_company.write_number(comp_breakdown_row, 9, sum(s['amount'] for s in benif_comp_stats.values()), sum_row_global_amt)
            else:
                sheet_company.merge_range(comp_row, 0, comp_row, 5, "Aucun chèque enregistré pour cet élément.", themes['reserve']['empty'])

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read()).decode('utf-8')
        output.close()
        return file_data
