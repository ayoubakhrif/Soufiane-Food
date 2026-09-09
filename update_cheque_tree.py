import os

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Try with ascii string if the unicode replace failed
old_tree_amount = "<field name=\"montant_encaisse\" readonly=\"state == 'encaisse'\" sum=\"Total Encaiss"
new_tree_amount = """<field name="montant_encaisse" readonly="state == 'encaisse'" sum="Total Encaissé"/>
                <field name="difference" sum="Total Différence" decoration-danger="difference != 0"/>"""

# we need to find the line containing old_tree_amount and replace the whole line
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'sum="Total Encaiss' in line and 'name="montant_encaisse"' in line:
        lines[i] = new_tree_amount

with open(filepath, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print("Added difference to tree")
