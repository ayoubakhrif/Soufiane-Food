import os

filepath = 'custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if "if rec.montant_encaisse != rec.amount_total:" in line and "action_annuler_encaissement" in "".join(lines[max(0, i-20):i]):
        skip = True
    if skip and "def action_annuler(self):" in line:
        skip = False
    
    if not skip:
        new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
