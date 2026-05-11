from odoo import models, fields, api

class ReportFinanceSituation(models.AbstractModel):
    _name = 'report.finance.report_finance_situation_template'
    _description = 'Rapport de Situation des Chèques Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Fetch physical cheques instead of datacheques (répartitions)
        physical_recs = self.env['finance.cheque.physical'].sudo().search([])
        
        active_list_phys = []
        reserve_list_phys = []
        bureau_list_phys = []
        annule_list_phys = []
        
        for physical in physical_recs:
            if not physical.datacheque_ids:
                continue
            # Use the first linked datacheque as the source of state and person
            first_datacheque = physical.datacheque_ids[0]
            state = first_datacheque.state or 'reserve'
            
            item = {
                'chq': physical.name,
                'ste': physical.ste_id.name or 'Inconnu',
                'perso': first_datacheque.perso_id.name or 'Inconnu',
                'benif': physical.benif_id.name or 'Inconnu',
                'amount': physical.amount_total or 0.0,
                'date_emission': physical.date_emission,
                'date_echeance': physical.date_echeance,
            }
            
            if state == 'actif':
                active_list_phys.append(item)
            elif state == 'reserve':
                reserve_list_phys.append(item)
            elif state == 'bureau':
                bureau_list_phys.append(item)
            elif state == 'annule':
                annule_list_phys.append(item)

        # 1. Active checks general recap (grouped by company)
        ste_summary = {}
        for item in active_list_phys:
            ste_name = item['ste']
            if ste_name not in ste_summary:
                ste_summary[ste_name] = {
                    'ste_name': ste_name,
                    'count': 0,
                    'total_amount': 0.0
                }
            ste_summary[ste_name]['count'] += 1
            ste_summary[ste_name]['total_amount'] += item['amount']

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

        return {
            'doc_ids': docids,
            'doc_model': 'finance.cheque.physical',
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
            
            'report_date': fields.Date.today().strftime('%d/%m/%Y'),
        }

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
                sheet_analysis = workbook.add_worksheet("Analyses Graphiques")
        sheet = workbook.add_worksheet("Situation des Chèques")
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
        sheet.merge_range(row, 2, row, 3, "Montant Global", sum_header_style)
        row += 1
        
        # Actif
        sheet.write(row, 0, "ACTIFS", sum_row_actif)
        sheet.write_number(row, 1, values['total_active_count'], sum_row_actif)
        sheet.merge_range(row, 2, row, 3, values['total_active_amount'], sum_row_actif_amt)
        row += 1
        # Reserve
        sheet.write(row, 0, "RÉSERVE", sum_row_reserve)
        sheet.write_number(row, 1, values['total_reserve_count'], sum_row_reserve)
        sheet.merge_range(row, 2, row, 3, values['total_reserve_amount'], sum_row_reserve_amt)
        row += 1
        # Bureau
        sheet.write(row, 0, "BUREAU", sum_row_bureau)
        sheet.write_number(row, 1, values['total_bureau_count'], sum_row_bureau)
        sheet.merge_range(row, 2, row, 3, values['total_bureau_amount'], sum_row_bureau_amt)
        row += 1
        # Annule
        sheet.write(row, 0, "ANNULÉS", sum_row_annule)
        sheet.write_number(row, 1, values['total_annule_count'], sum_row_annule)
        sheet.merge_range(row, 2, row, 3, values['total_annule_amount'], sum_row_annule_amt)
        row += 1
        # Global Total
        sheet.write(row, 0, "TOTAL GENERAL", sum_row_global)
        sheet.write_number(row, 1, values['global_count'], sum_row_global)
        sheet.merge_range(row, 2, row, 3, values['global_amount'], sum_row_global_amt)
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

        # ----------------------------------------------------
        # 5. CHARTS & GRAPHS (Inserted in the ANALYSES sheet)
        # ----------------------------------------------------
        # Chart 1: Doughnut Chart for States Distribution
        chart_state = workbook.add_chart({'type': 'doughnut'})
        chart_state.add_series({
            'categories': "='Situation des Chèques'!$A$4:$A$7",
            'values': "='Situation des Chèques'!$C$4:$C$7",
            'points': [
                {'fill': {'color': '#137333'}},  # Actif (Green)
                {'fill': {'color': '#B06000'}},  # Reserve (Orange)
                {'fill': {'color': '#1A73E8'}},  # Bureau (Blue)
                {'fill': {'color': '#C5221F'}},  # Annule (Red)
            ],
            'name': 'Montant Global par État',
            'data_labels': {'percentage': True, 'position': 'outside_end'}
        })
        chart_state.set_title({
            'name': 'Répartition Financière par État',
            'name_font': {'bold': True, 'size': 14, 'color': '#1A4D80'}
        })
        chart_state.set_style(10)
        chart_state.set_size({'width': 500, 'height': 350})
        sheet_analysis.insert_chart('A3', chart_state)

        # Chart 2: Column Chart for Active Checks per Company (if any exist)
        if values.get('active_summary') and start_row_active_excel <= end_row_active_excel:
            chart_active = workbook.add_chart({'type': 'column'})
            chart_active.add_series({
                'categories': f"='Situation des Chèques'!$A${start_row_active_excel}:$A${end_row_active_excel}",
                'values': f"='Situation des Chèques'!$C${start_row_active_excel}:$C${end_row_active_excel}",
                'fill': {'color': '#137333'},
                'name': 'Montant Total Actif (MAD)',
                'data_labels': {'value': True, 'font': {'size': 10, 'color': '#137333'}}
            })
            chart_active.set_title({
                'name': 'Encours Actif par Société',
                'name_font': {'bold': True, 'size': 14, 'color': '#137333'}
            })
            chart_active.set_x_axis({
                'name': 'Sociétés Émettrices',
                'name_font': {'size': 10, 'bold': True},
                'num_font': {'size': 9, 'rotation': -15}
            })
            chart_active.set_y_axis({
                'name': 'Montant Cumulé (MAD)',
                'name_font': {'size': 10, 'bold': True},
                'num_font': {'size': 9}
            })
            chart_active.set_legend({'none': True})
            chart_active.set_style(11)
            chart_active.set_size({'width': 850, 'height': 450})
            sheet_analysis.insert_chart('A21', chart_active)
            
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read()).decode('utf-8')
        output.close()
        return file_data
