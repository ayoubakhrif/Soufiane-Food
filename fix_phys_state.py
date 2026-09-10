import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("is_encaisse = phys.state == 'encaisse' or phys.encours == 'encaisse'", "is_encaisse = phys.encours == 'encaisse'")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed phys.state")
