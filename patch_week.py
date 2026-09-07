import re

with open('custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update week_match to capture 'encaisse'
old_match = r'week_match = re.match(r"^(?:w|s|semaine|week)\s*0*(\d{1,2})$", msg_clean)'
new_match = r'''week_match = re.match(r"^(encaisse\s+)?(?:w|s|semaine|week)\s*0*(\d{1,2})$", msg_clean)'''
content = content.replace(old_match, new_match)

# 2. Update capturing group
old_week_num = r'week_num = int(week_match.group(1))'
new_week_num = r'''only_encaisse = bool(week_match.group(1))
            week_num = int(week_match.group(2))'''
content = content.replace(old_week_num, new_week_num)

# 3. Apply filter before missing_journals check
old_queries = r'''            datacheques = request.env['datacheque'].sudo().search([('week', '=', week_str)], order='journal asc')
            effets = request.env['finance.effet'].sudo().search([('week', '=', week_str)])
            cheques_v2 = request.env['finance2.cheque'].sudo().search([('week', '=', week_str)], order='journal asc')'''

new_queries = r'''            datacheques = request.env['datacheque'].sudo().search([('week', '=', week_str)], order='journal asc')
            effets = request.env['finance.effet'].sudo().search([('week', '=', week_str)])
            cheques_v2 = request.env['finance2.cheque'].sudo().search([('week', '=', week_str)], order='journal asc')
            
            if only_encaisse:
                datacheques = datacheques.filtered(lambda dq: dq.date_encaissement or (dq.physical_cheque_id and dq.physical_cheque_id.encours == 'encaisse'))
                effets = effets.filtered(lambda e: e.date_encaissement or e.state == 'encaisse')
                cheques_v2 = cheques_v2.filtered(lambda c: c.date_encaissement)'''
content = content.replace(old_queries, new_queries)

# 4. Modify document generation for deduplication
old_doc_gen = r'''            documents = []
            total_amount = 0.0
            
            # Group datacheques by physical cheque
            grouped_dqs = {}
            for dq in datacheques:
                phys = dq.physical_cheque_id
                if not phys:
                    continue
                if phys not in grouped_dqs:
                    grouped_dqs[phys] = []
                grouped_dqs[phys].append(dq)
                total_amount += dq.amount
                
            def get_min_journal(dqs_list):
                journals = [dq.journal for dq in dqs_list if dq.journal]
                return min(journals) if journals else float('inf')
                
            for phys, dqs in grouped_dqs.items():
                documents.append({
                    'type_doc': 'CHQ',
                    'obj': phys,
                    'items': dqs,
                    'min_journal': get_min_journal(dqs)
                })
                
            for e in effets:
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
                total_amount += c_v2.amount_total'''

new_doc_gen = r'''            documents = []
            total_amount = 0.0
            seen_cheques = set()
            
            for c_v2 in cheques_v2:
                c_key = (str(c_v2.name).strip(), c_v2.ste_id.id if c_v2.ste_id else False)
                seen_cheques.add(c_key)
                documents.append({
                    'type_doc': 'CHQ_V2',
                    'obj': c_v2,
                    'items': c_v2.repartition_ids,
                    'min_journal': int(c_v2.journal) if c_v2.journal and c_v2.journal.isdigit() else float('inf')
                })
                total_amount += c_v2.amount_total

            # Group datacheques by physical cheque
            grouped_dqs = {}
            for dq in datacheques:
                phys = dq.physical_cheque_id
                if not phys:
                    continue
                c_key = (str(phys.name).strip(), phys.ste_id.id if phys.ste_id else False)
                if c_key in seen_cheques:
                    continue
                if phys not in grouped_dqs:
                    grouped_dqs[phys] = []
                grouped_dqs[phys].append(dq)
                total_amount += dq.amount
                
            def get_min_journal(dqs_list):
                journals = [dq.journal for dq in dqs_list if dq.journal]
                return min(journals) if journals else float('inf')
                
            for phys, dqs in grouped_dqs.items():
                documents.append({
                    'type_doc': 'CHQ',
                    'obj': phys,
                    'items': dqs,
                    'min_journal': get_min_journal(dqs)
                })
                
            for e in effets:
                documents.append({
                    'type_doc': 'EFFET',
                    'obj': e,
                    'items': [e],
                    'min_journal': float('inf') # Display effets at the bottom
                })
                total_amount += e.montant'''

content = content.replace(old_doc_gen, new_doc_gen)

with open('custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated successfully")
