import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = """                        for dq in dqs:
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
                            s_label = s_dict.get(dq.state) or str(dq.state)"""

new_code = """                        for dq in dqs:
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
                            s_label = s_dict.get(getattr(dq, 'state', '')) or str(getattr(dq, 'state', ''))"""

content = content.replace(old_code, new_code)

# Check if there are other dq.amount or similar outside of this
content = content.replace("total_amount += dq.amount", "total_amount += getattr(dq, 'amount', 0.0)")
content = content.replace("if dq.journal: chq_vide_missing_journals.add(str(dq.journal))", "if getattr(dq, 'journal', False): chq_vide_missing_journals.add(str(dq.journal))")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed datacheque attributes")
