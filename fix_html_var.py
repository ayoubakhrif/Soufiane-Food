import os

api_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2\controllers\whatsapp_finance_api.py'
with open(api_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("html_table +=", "html_content +=")

with open(api_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed html_table to html_content")
