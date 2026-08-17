import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_confirmer = """            if not rec.journal:
                missing_fields.append("Journal")"""

new_confirmer = """            if not rec.journal or rec.journal.strip() == '0':
                missing_fields.append("Journal (doit être différent de 0)")"""

content = content.replace(old_confirmer, new_confirmer)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated cheque.py journal validation.")
