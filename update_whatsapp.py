import os
import re

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to replace the PDF generation part in handle week search
# Let's locate the start of html_content in the week search

pattern = r'encaisse_label = " ENCAISSÉS" if only_encaisse else ""\s*html_content = f"""(.*?)pdf_base64 = base64.b64encode\(pdf_content\).decode\(\'utf-8\'\)'
# Wait, there's special characters, I'll use simple string splitting

parts = content.split('encaisse_label = " ENCAISSÉS" if only_encaisse else ""')
if len(parts) < 2:
    parts = content.split('encaisse_label = " ENCAISS\\xc9S" if only_encaisse else ""')

part1 = parts[0]
rest = parts[1]

parts2 = rest.split("pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')")
part3 = parts2[1]

# Now let's build the new Excel generation code
new_code = """encaisse_label = " ENCAISSÉS" if only_encaisse else ""
            
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
                            sheet.write(row_idx, 5, rep.benif_id.name if rep.benif_id else '', cell_format)
                            sheet.write(row_idx, 6, rep.serie_facture or '', cell_format)
                            sheet.write(row_idx, 7, rep.bl or '', cell_format)
                            sheet.write(row_idx, 8, 'Oui' if c_v2.doc_pdf else 'Non', cell_center)
                            sheet.write(row_idx, 9, dict(c_v2._fields['type'].selection).get(c_v2.type) or 'Chèque', cell_format)
                            sheet.write(row_idx, 10, dict(rep._fields['state'].selection).get(rep.state) or rep.state, cell_format)
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
                    
                    is_encaisse = phys.state == 'encaisse' or phys.encours == 'encaisse'
                    etat_label = "Encaissé" if is_encaisse else "En cours"
                    doc_display = f"CHQ {doc_name}"
                    chq_pdf_icon = "Oui" if phys.chq_vide_pdf else "Non"
                    
                    if not phys.chq_vide_pdf:
                        for dq in dqs:
                            if dq.journal: chq_vide_missing_journals.add(str(dq.journal))
                            
                    grouped_rows = []
                    for dq in dqs:
                        journal_val = dq.journal or "N/A"
                        benif_name = dq.benif_id.name if dq.benif_id else "N/A"
                        dq_amount = dq.amount
                        serie_val = dq.serie_facture or "N/A"
                        bl_val = dq.bl or "N/A"
                        doc_pdf_icon = "Oui" if dq.doc_pdf else "Non"
                        
                        if not dq.doc_pdf and dq.journal:
                            doc_missing_journals.add(str(dq.journal))
                            
                        t_dict = dict(dq._fields['type'].selection)
                        t_label = t_dict.get(dq.type) or str(dq.type)
                        s_dict = dict(dq._fields['state'].selection)
                        s_label = s_dict.get(dq.state) or str(dq.state)
                        
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
                    sheet.write(row_idx, 10, e.state or "N/A", cell_format)
                    sheet.write(row_idx, 11, e.montant, cell_format)
                    sheet.write(row_idx, 12, e.montant, cell_format)
                    sheet.write(row_idx, 13, "Encaissé" if e.state == 'encaisse' else "En cours", cell_format)
                    row_idx += 1
            
            sheet.write(row_idx, 11, "Total:", bold)
            sheet.write(row_idx, 12, total_amount, bold)
            
            workbook.close()
            output.seek(0)
            xlsx_base64 = base64.b64encode(output.read()).decode('utf-8')"""

# We also need to change the returned file dictionary from pdf to xlsx
part3 = part3.replace("'pdf_base64': pdf_base64", "'pdf_base64': xlsx_base64")
part3 = part3.replace(".pdf\"", ".xlsx\"")
part3 = part3.replace("Erreur lors de la gén\xc3\xa9ration du PDF", "Erreur lors de la génération du fichier Excel")

content = part1 + new_code + part3

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated WhatsApp API")
