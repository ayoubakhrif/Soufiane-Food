import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace timeout=120 with timeout=240
content = content.replace("timeout=120", "timeout=240")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated timeout from 120 to 240")
