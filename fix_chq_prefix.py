import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('doc_display = f"CHQ {doc_name}"', 'doc_display = str(doc_name)')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Removed CHQ prefix")
