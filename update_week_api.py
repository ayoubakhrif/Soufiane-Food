import os
import re

api_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2\controllers\whatsapp_finance_api.py'
with open(api_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the search block
old_search = """            datacheques = request.env['datacheque'].sudo().search([('week', '=', week_str)], order='journal asc')
            effets = request.env['finance.effet'].sudo().search([('week', '=', week_str)])
            
            if not datacheques and not effets:
                return {'status': 'not_found', 'message': f"Aucun document trouvé pour la semaine {week_str}."}"""

new_search = """            datacheques = request.env['datacheque'].sudo().search([('week', '=', week_str)], order='journal asc')
            effets = request.env['finance.effet'].sudo().search([('week', '=', week_str)])
            cheques_v2 = request.env['finance2.cheque'].sudo().search([('week', '=', week_str)], order='journal asc')
            
            if not datacheques and not effets and not cheques_v2:
                return {'status': 'not_found', 'message': f"Aucun document trouvé pour la semaine {week_str}."}"""

content = content.replace(old_search, new_search)

# 2. Append cheques_v2 to documents
old_append_effets = """            for e in effets:
                documents.append({
                    'type_doc': 'EFFET',
                    'obj': e,
                    'items': [e],
                    'min_journal': float('inf') # Display effets at the bottom
                })
                total_amount += e.montant"""

new_append_v2 = """            for e in effets:
                documents.append({
                    'type_doc': 'EFFET',
                    'obj': e,
                    'items': [e],
                    'min_journal': float('inf') # Display effets at the bottom
                })
                total_amount += e.montant
                
            for c_v2 in cheques_v2:
                documents.append({
                    'type_doc': 'CHQ_V2',
                    'obj': c_v2,
                    'items': c_v2.repartition_ids,
                    'min_journal': int(c_v2.journal) if c_v2.journal and c_v2.journal.isdigit() else float('inf')
                })
                total_amount += c_v2.amount_total"""

content = content.replace(old_append_effets, new_append_v2)

# 3. Update the HTML renderer
old_html_logic = """            for doc in documents:
                if doc['type_doc'] == 'CHQ':
                    phys = doc['obj']
                    dqs = doc['items']"""

new_html_logic = """            for doc in documents:
                if doc['type_doc'] == 'CHQ_V2':
                    c_v2 = doc['obj']
                    reps = doc['items']
                    
                    doc_name = c_v2.name or "N/A"
                    ste_name = c_v2.ste_id.name if c_v2.ste_id else "N/A"
                    phys_amount = '{:,.2f}'.format(c_v2.amount_total).replace(',', ' ')
                    
                    global_state_dict = dict(c_v2._fields['state'].selection)
                    global_state = global_state_dict.get(c_v2.state) or c_v2.state
                    
                    if not reps:
                        html_table += "<tr>"
                        html_table += f"<td>{doc_name}</td>"
                        html_table += f"<td>{'Oui' if c_v2.chq_vide_pdf else 'Non'}</td>"
                        html_table += f"<td>{c_v2.date_emission.strftime('%d/%m/%Y') if c_v2.date_emission else ''}</td>"
                        html_table += f"<td>{ste_name}</td>"
                        html_table += f"<td>{c_v2.journal or ''}</td>"
                        html_table += f"<td>{c_v2.benif_id.name if c_v2.benif_id else ''}</td>"
                        html_table += f"<td>{c_v2.serie_facture or ''}</td>"
                        html_table += "<td>-</td>"
                        html_table += f"<td>{'Oui' if c_v2.doc_pdf else 'Non'}</td>"
                        html_table += f"<td>{dict(c_v2._fields['type'].selection).get(c_v2.type) or 'Chèque'}</td>"
                        html_table += "<td>-</td>"
                        html_table += f"<td>{phys_amount}</td>"
                        html_table += f"<td>{phys_amount}</td>"
                        html_table += f"<td>{global_state}</td>"
                        html_table += "</tr>"
                    else:
                        for idx, rep in enumerate(reps):
                            html_table += "<tr>"
                            if idx == 0:
                                row_span = len(reps)
                                html_table += f"<td rowspan='{row_span}'>{doc_name}</td>"
                                html_table += f"<td rowspan='{row_span}'>{'Oui' if c_v2.chq_vide_pdf else 'Non'}</td>"
                                html_table += f"<td rowspan='{row_span}'>{c_v2.date_emission.strftime('%d/%m/%Y') if c_v2.date_emission else ''}</td>"
                                html_table += f"<td rowspan='{row_span}'>{ste_name}</td>"
                            
                            html_table += f"<td>{c_v2.journal or ''}</td>"
                            html_table += f"<td>{c_v2.benif_id.name if c_v2.benif_id else ''}</td>"
                            html_table += f"<td>{rep.serie_facture or ''}</td>"
                            html_table += f"<td>{rep.bl or ''}</td>"
                            
                            if idx == 0:
                                html_table += f"<td rowspan='{row_span}'>{'Oui' if c_v2.doc_pdf else 'Non'}</td>"
                            
                            html_table += f"<td>{dict(rep._fields['type'].selection).get(rep.type) or ''}</td>"
                            html_table += f"<td>{dict(rep._fields['encours'].selection).get(rep.encours) or ''}</td>"
                            html_table += f"<td>{'{:,.2f}'.format(rep.amount).replace(',', ' ')}</td>"
                            
                            if idx == 0:
                                html_table += f"<td rowspan='{row_span}'>{phys_amount}</td>"
                                html_table += f"<td rowspan='{row_span}'>{global_state}</td>"
                                
                            html_table += "</tr>"

                elif doc['type_doc'] == 'CHQ':
                    phys = doc['obj']
                    dqs = doc['items']"""

content = content.replace(old_html_logic, new_html_logic)

with open(api_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated whatsapp_finance_api.py for week search")
