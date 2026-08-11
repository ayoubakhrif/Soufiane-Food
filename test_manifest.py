import ast
with open('c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/__manifest__.py', 'r', encoding='utf-8') as f:
    data = f.read()
try:
    manifest = ast.literal_eval(data)
    print("Parsed successfully:", manifest['name'])
except Exception as e:
    print("Error parsing:", str(e))
