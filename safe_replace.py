import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Locate the start of HTML generation
start_marker = 'encaisse_label = " ENCAISSÉS" if only_encaisse else ""'
if start_marker not in content:
    start_marker = 'encaisse_label = " ENCAISS\\xc9S" if only_encaisse else ""'

start_idx = content.find(start_marker)

# Locate the except Exception block
end_marker = "            except Exception as e:\n"
end_idx = content.find(end_marker, start_idx)

# We will replace from start_idx to end_idx with our new Excel generation logic
excel_logic = """encaisse_label = " ENCAISSÉS" if only_encaisse else ""
            
            try:
                import io
                import xlsxwriter
                
                output = io.BytesIO()
                workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                sheet = workbook.add_worksheet(f"Semaine {week_str}")
                
                bold = workbook.add_format({'bold': True, 'bg_color': '#ecf0f1', 'border': 1})
                cell_format = workbook.add_format({'border': 1, 'valign': 'vcenter'})
                cell_center = workbook.add_format({'border': 1, 'valign': 'vcenter', 'align': 'center'})
                
                headers = ["Document", "Chq Vide", "Date d'Émission", "Société", "N° Journal", "Bénéficiaire", "Série de Facture", "BL", "Doc PDF", "Type", "Statut", "Montant Ligne", "Montant Total (DH)", "État"]
                for col, h in enumerate(headers):
                    sheet.write(0, col, h, bold)
                    
                chq_vide_missing_journals = set()
                doc_missing_journals = set()
                row_idx = 1
                
                for doc in documents:
                    if doc['type_doc'] == 'CHQ_V2':
                        c_v2 = doc['obj']
                        reps = doc['items']
                        doc_name = c_v2.name or "N/A"
                        ste_name = c_v2.ste_id.name if c_v2.ste_id else "N/A"
                        phys_amount = c_v2.amount_total
                        
                        global_state_dict = dict(c_v2._fields['state'].selection)
                        global_state = global_state_dict.get(c_v2.state) or c_v2.state
                        
                        if not c_v2.chq_vide_pdf:
                            if reps:
                                for rep in reps:
                                    if rep.journal:
                                        chq_vide_missing_journals.add(str(rep.journal))
                            elif c_v2.journal:
                                chq_vide_missing_journals.add(str(c_v2.journal))
                                
                        if not c_v2.doc_pdf:
                            if reps:
                                for rep in reps:
                                    if rep.journal:
                                        doc_missing_journals.add(str(rep.journal))
                            elif c_v2.journal:
                                doc_missing_journals.add(str(c_v2.journal))
                        
                        if not reps:
                            sheet.write(row_idx, 0, doc_name, cell_format)
                            sheet.write(row_idx, 1, 'Oui' if c_v2.chq_vide_pdf else 'Non', cell_center)
                            sheet.write(row_idx, 2, c_v2.date_emission.strftime('%d/%m/%Y') if c_v2.date_emission else '', cell_format)
                            sheet.write(row_idx, 3, ste_name, cell_format)
                            sheet.write(row_idx, 4, c_v2.journal or '', cell_format)
                            sheet.write(row_idx, 5, c_v2.benif_id.name if c_v2.benif_id else '', cell_format)
                            sheet.write(row_idx, 6, '-', cell_center)
                            sheet.write(row_idx, 7, '-', cell_center)
                            sheet.write(row_idx, 8, 'Oui' if c_v2.doc_pdf else 'Non', cell_center)
                            sheet.write(row_idx, 9, dict(c_v2._fields['type'].selection).get(c_v2.type) or 'Chèque', cell_format)
                            sheet.write(row_idx, 10, '-', cell_center)
                            sheet.write(row_idx, 11, phys_amount, cell_format)
                            sheet.write(row_idx, 12, phys_amount, cell_format)
                            sheet.write(row_idx, 13, global_state, cell_format)
                            row_idx += 1
                        else:
                            for idx, rep in enumerate(reps):
                                sheet.write(row_idx, 0, doc_name, cell_format)
                                sheet.write(row_idx, 1, 'Oui' if c_v2.chq_vide_pdf else 'Non', cell_center)
                                sheet.write(row_idx, 2, c_v2.date_emission.strftime('%d/%m/%Y') if c_v2.date_emission else '', cell_format)
                                sheet.write(row_idx, 3, ste_name, cell_format)
                                sheet.write(row_idx, 4, rep.journal or '', cell_format)
                                sheet.write(row_idx, 5, c_v2.benif_id.name if c_v2.benif_id else '', cell_format)
                                sheet.write(row_idx, 6, rep.serie_facture or '', cell_format)
                                sheet.write(row_idx, 7, rep.bl or '', cell_format)
                                sheet.write(row_idx, 8, 'Oui' if c_v2.doc_pdf else 'Non', cell_center)
                                sheet.write(row_idx, 9, dict(c_v2._fields['type'].selection).get(c_v2.type) or 'Chèque', cell_format)
                                sheet.write(row_idx, 10, '-', cell_format)
                                sheet.write(row_idx, 11, rep.amount, cell_format)
                                sheet.write(row_idx, 12, phys_amount if idx == 0 else '', cell_format)
                                sheet.write(row_idx, 13, global_state if idx == 0 else '', cell_format)
                                row_idx += 1
                    elif doc['type_doc'] == 'CHQ':
                        phys = doc['obj']
                        dqs = doc['items']
                        
                        doc_name = phys.name or "N/A"
                        ste_name = phys.ste_id.name if phys.ste_id else "N/A"
                        phys_amount = phys.amount_total
                        date_em = phys.date_emission.strftime('%d/%m/%Y') if phys.date_emission else "N/A"
                        
                        is_encaisse = getattr(phys, 'encours', '') == 'encaisse'
                        etat_label = "Encaissé" if is_encaisse else "En cours"
                        doc_display = f"CHQ {doc_name}"
                        chq_pdf_icon = "Oui" if getattr(phys, 'chq_vide_pdf', False) else "Non"
                        
                        if not getattr(phys, 'chq_vide_pdf', False):
                            for dq in dqs:
                                if getattr(dq, 'journal', False): chq_vide_missing_journals.add(str(dq.journal))
                                
                        grouped_rows = []
                        for dq in dqs:
                            journal_val = getattr(dq, 'journal', False) or "N/A"
                            benif_name = dq.benif_id.name if getattr(dq, 'benif_id', False) else "N/A"
                            dq_amount = getattr(dq, 'amount', 0.0)
                            serie_val = getattr(dq, 'serie_facture', getattr(dq, 'serie', "N/A")) or "N/A"
                            bl_val = getattr(dq, 'bl', "N/A") or "N/A"
                            doc_pdf_icon = "Oui" if getattr(dq, 'doc_pdf', False) else "Non"
                            
                            if not getattr(dq, 'doc_pdf', False) and getattr(dq, 'journal', False):
                                doc_missing_journals.add(str(dq.journal))
                                
                            t_dict = dict(dq._fields['type'].selection) if 'type' in dq._fields else {}
                            t_label = t_dict.get(getattr(dq, 'type', '')) or str(getattr(dq, 'type', ''))
                            s_dict = dict(dq._fields['state'].selection) if 'state' in dq._fields else {}
                            s_label = s_dict.get(getattr(dq, 'state', '')) or str(getattr(dq, 'state', ''))
                            
                            grouped_rows.append({
                                'journal': journal_val,
                                'benif': benif_name,
                                'items': [{'type': t_label, 'state': s_label, 'amount': dq_amount, 'serie': serie_val, 'bl': bl_val, 'doc_pdf_icon': doc_pdf_icon}]
                            })
                            
                        for g_idx, group in enumerate(grouped_rows):
                            for i_idx, item in enumerate(group['items']):
                                sheet.write(row_idx, 0, doc_display, cell_format)
                                sheet.write(row_idx, 1, chq_pdf_icon, cell_center)
                                sheet.write(row_idx, 2, date_em, cell_format)
                                sheet.write(row_idx, 3, ste_name, cell_format)
                                sheet.write(row_idx, 4, group['journal'], cell_format)
                                sheet.write(row_idx, 5, group['benif'], cell_format)
                                sheet.write(row_idx, 6, item['serie'], cell_format)
                                sheet.write(row_idx, 7, item['bl'], cell_format)
                                sheet.write(row_idx, 8, item['doc_pdf_icon'], cell_center)
                                sheet.write(row_idx, 9, item['type'], cell_format)
                                sheet.write(row_idx, 10, item['state'], cell_format)
                                sheet.write(row_idx, 11, item['amount'], cell_format)
                                sheet.write(row_idx, 12, phys_amount if g_idx == 0 and i_idx == 0 else '', cell_format)
                                sheet.write(row_idx, 13, etat_label if g_idx == 0 and i_idx == 0 else '', cell_format)
                                row_idx += 1
                    else: # EFFET
                        e = doc['obj']
                        sheet.write(row_idx, 0, f"EFFET {e.serie or 'N/A'}", cell_format)
                        sheet.write(row_idx, 1, "-", cell_center)
                        sheet.write(row_idx, 2, e.date_emission.strftime('%d/%m/%Y') if e.date_emission else "N/A", cell_format)
                        sheet.write(row_idx, 3, e.ste_id.name if e.ste_id else "N/A", cell_format)
                        sheet.write(row_idx, 4, "N/A", cell_format)
                        sheet.write(row_idx, 5, e.benif_id.name if e.benif_id else "N/A", cell_format)
                        sheet.write(row_idx, 6, "N/A", cell_format)
                        sheet.write(row_idx, 7, "N/A", cell_format)
                        sheet.write(row_idx, 8, "-", cell_center)
                        sheet.write(row_idx, 9, "Effet", cell_format)
                        sheet.write(row_idx, 10, getattr(e, 'state', "N/A"), cell_format)
                        sheet.write(row_idx, 11, e.montant, cell_format)
                        sheet.write(row_idx, 12, e.montant, cell_format)
                        sheet.write(row_idx, 13, "Encaissé" if getattr(e, 'state', '') == 'encaisse' else "En cours", cell_format)
                        row_idx += 1
                
                sheet.write(row_idx, 11, "Total:", bold)
                sheet.write(row_idx, 12, total_amount, bold)
                
                workbook.close()
                output.seek(0)
                xlsx_base64 = base64.b64encode(output.read()).decode('utf-8')
    
                return {
                    'status': 'success',
                    'product_name': f"Chèques{encaisse_label.title()} Semaine {week_str}",
                    'response': f"Voici le rapport des chèques{encaisse_label.lower()} pour la semaine *{week_str}*." + 
                                (f"\n\n⚠️ *Journaux manquants ({len(missing_journals)} chqs) :* {', '.join(map(str, missing_journals))}" if missing_journals else "") +
                                (f"\n\n❌ *Chq vide absent ({len(chq_vide_missing_journals)} chqs) :* Les journaux des chqs sans pdf de chq vide: {', '.join(sorted(chq_vide_missing_journals))}" if chq_vide_missing_journals else "") +
                                (f"\n\n❌ *Documentation absente ({len(doc_missing_journals)} chqs) :* Journaux des chqs sans pdf de documentation: {', '.join(sorted(doc_missing_journals))}" if doc_missing_journals else ""),
                    'files': [
                        {
                            'pdf_base64': xlsx_base64,
                            'file_name': f"Cheques_{week_str}{'_encaisses' if only_encaisse else ''}.xlsx",
                            'caption': f"Chèques{encaisse_label.lower()} de la semaine {week_str} 📅"
                        }
                    ]
                }
"""

content = content[:start_idx] + excel_logic + content[end_idx:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Restored bottom half of the file and applied safer excel logic!")
