with open('custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_func = """            def get_min_journal(dqs_list):
                journals = [dq.journal for dq in dqs_list if dq.journal]
                return min(journals) if journals else float('inf')"""

new_func = """            def get_min_journal(dqs_list):
                journals = [int(dq.journal) for dq in dqs_list if dq.journal and str(dq.journal).isdigit()]
                return min(journals) if journals else float('inf')"""

content = content.replace(old_func, new_func)

with open('custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed get_min_journal")
