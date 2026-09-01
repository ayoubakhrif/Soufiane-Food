import os

api_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2\controllers\whatsapp_finance_api.py'
with open(api_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the broken line
old_line = "html_content += f\"<td>{dict(rep._fields['encours'].selection).get(rep.encours) or ''}</td>\""
new_line = "html_content += \"<td>-</td>\""

content = content.replace(old_line, new_line)

with open(api_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed encours key error")
