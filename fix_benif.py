import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("rep.benif_id.name if rep.benif_id else ''", "c_v2.benif_id.name if c_v2.benif_id else ''")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed rep.benif_id")
