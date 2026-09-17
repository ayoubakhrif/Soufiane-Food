import os

filepath = 'custom-addons/finance_2/__manifest__.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

if "'reports/divers_report.xml'" not in content:
    content = content.replace("'security/ir.model.access.csv',", "'security/ir.model.access.csv',\n        'reports/divers_report.xml',")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
print("Updated manifest")
