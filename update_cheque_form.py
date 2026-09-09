import os

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
for i, line in enumerate(lines):
    if 'name="montant_encaisse"' in line and 'invisible=' in line: # In the form view group
        lines[i] = line + '\n                            <field name="difference" invisible="state in (\'brouillon\', \'reserve\', \'actif\')"/>'

with open(filepath, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print("Added difference to form")
