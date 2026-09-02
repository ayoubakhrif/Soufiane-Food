import os
import re

base_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2'
api_path = os.path.join(base_path, 'controllers', 'whatsapp_finance_api.py')
cheque_model_path = os.path.join(base_path, 'models', 'cheque.py')
cheque_views_path = os.path.join(base_path, 'views', 'cheque_views.xml')

# 1. Update Whatsapp API (manque logic + missing journals logic)
with open(api_path, 'r', encoding='utf-8') as f:
    api_content = f.read()

# 1.a) Missing journals for V2 cheques
# Currently it only looks at datacheques:
# missing_journals = []
# if datacheques: ...
old_missing_journals = """            # Calculate missing journals
            missing_journals = []
            if datacheques:
                journals = [int(dq.journal) for dq in datacheques if dq.journal and int(dq.journal) > 0]
                if journals:
                    max_j = max(journals)
                    expected_set = set(range(1, max_j + 1))
                    actual_set = set(journals)
                    missing_journals = sorted(list(expected_set - actual_set))"""

new_missing_journals = """            # Calculate missing journals
            missing_journals = []
            journals = [int(dq.journal) for dq in datacheques if dq.journal and int(dq.journal) > 0]
            # Add V2 cheques to journals
            for c_v2 in cheques_v2:
                if c_v2.repartition_ids:
                    for rep in c_v2.repartition_ids:
                        if rep.journal and rep.journal.isdigit():
                            journals.append(int(rep.journal))
                elif c_v2.journal and c_v2.journal.isdigit():
                    journals.append(int(c_v2.journal))
                    
            if journals:
                max_j = max(journals)
                expected_set = set(range(1, max_j + 1))
                actual_set = set(journals)
                missing_journals = sorted(list(expected_set - actual_set))"""

api_content = api_content.replace(old_missing_journals, new_missing_journals)

# 1.b) Add chq_vide_missing_journals and doc_missing_journals tracking for V2
# Inside CHQ_V2 block
old_v2_html = """                    global_state_dict = dict(c_v2._fields['state'].selection)
                    global_state = global_state_dict.get(c_v2.state) or c_v2.state
                    
                    if not reps:"""

new_v2_html = """                    global_state_dict = dict(c_v2._fields['state'].selection)
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
                    
                    if not reps:"""

api_content = api_content.replace(old_v2_html, new_v2_html)

# 1.c) Manque logic for V2
# Inside Handle Manque Search (Missing PDFs)
old_manque_search = """            # Search cheques with missing PDFs
            domain.extend(['|', ('doc_pdf', '=', False), ('chq_vide_pdf', '=', False)])
            
            phys_cheques = request.env['finance.cheque.physical'].sudo().search(domain, order='date_emission desc', limit=100)
            
            if not phys_cheques:
                return {'status': 'not_found', 'message': f"🚫 Aucun chèque manquant de PDF trouvé ({filter_desc})."}
            
            msg = f"📁 *Chèques avec PDF manquants ({filter_desc})*\\n\\n"
            count = 0
            excel_data = []
            for phys in phys_cheques:"""

new_manque_search = """            # Search cheques with missing PDFs
            domain.extend(['|', ('doc_pdf', '=', False), ('chq_vide_pdf', '=', False)])
            
            phys_cheques = request.env['finance.cheque.physical'].sudo().search(domain, order='date_emission desc', limit=100)
            v2_cheques = request.env['finance2.cheque'].sudo().search(domain, order='date_emission desc', limit=100)
            
            if not phys_cheques and not v2_cheques:
                return {'status': 'not_found', 'message': f"🚫 Aucun chèque manquant de PDF trouvé ({filter_desc})."}
            
            msg = f"📁 *Chèques avec PDF manquants ({filter_desc})*\\n\\n"
            count = 0
            excel_data = []
            for c_v2 in v2_cheques:
                missing = []
                c_v2_check = c_v2.sudo().with_context(bin_size=True)
                if not c_v2_check.doc_pdf:
                    missing.append("Documentation")
                if not c_v2_check.chq_vide_pdf:
                    missing.append("Chèque vide")
                
                if missing:
                    ste_name = c_v2.ste_id.name if c_v2.ste_id else 'N/A'
                    factures = ", ".join(filter(None, [d.serie_facture for d in c_v2.repartition_ids]))
                    
                    fact_display = f" [Série de facture: {factures}]" if factures else ""
                    msg += f"▪️ *{c_v2.name}*{fact_display} ({ste_name}) ⚠️ Manque : {', '.join(missing)}\\n"

            for phys in phys_cheques:"""

api_content = api_content.replace(old_manque_search, new_manque_search)

with open(api_path, 'w', encoding='utf-8') as f:
    f.write(api_content)

# 2. Rename Montant total to Montant des factures in cheque.py
with open(cheque_model_path, 'r', encoding='utf-8') as f:
    model_content = f.read()

model_content = model_content.replace("amount_total = fields.Float(string='Montant Total', tracking=True)", "amount_total = fields.Float(string='Montant des factures', tracking=True)")

with open(cheque_model_path, 'w', encoding='utf-8') as f:
    f.write(model_content)

# 3. Rename Montant total to Montant des factures in cheque_views.xml
with open(cheque_views_path, 'r', encoding='utf-8') as f:
    views_content = f.read()

# Just in case there is a string override in XML
if "string=\"Montant Total\"" in views_content:
    views_content = views_content.replace("string=\"Montant Total\"", "string=\"Montant des factures\"")

with open(cheque_views_path, 'w', encoding='utf-8') as f:
    f.write(views_content)

print("Updates completed.")
