import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_init = """                chq_vide_missing_journals = set()
                doc_missing_journals = set()
                row_idx = 1"""

content = content.replace("                row_idx = 1", new_init)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added sets initialization")
