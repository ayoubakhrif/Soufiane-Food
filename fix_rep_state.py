import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("dict(rep._fields['state'].selection).get(rep.state) or rep.state", "'-'")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed rep.state")
