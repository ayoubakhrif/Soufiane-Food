import os
import re

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r'<button name="action_remettre_finance"[^>]+/>'
replacement = '<button name="action_remettre_finance" string="Remettre en Brouillon" type="object" groups="finance_2.group_finance2_manager" invisible="state not in (\'reserve\', \'actif\')" confirm="Voulez-vous vraiment remettre ce chèque en brouillon ?"/>'

content = re.sub(pattern, replacement, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Button updated successfully")
