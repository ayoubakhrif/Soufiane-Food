import os

def remove_bom(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    if content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
        with open(filepath, 'wb') as f:
            f.write(content)
        print(f"Removed BOM from {filepath}")

for root, dirs, files in os.walk(r'c:\odoo-repos\Soufiane-Food\custom-addons\stock_casa_field'):
    for file in files:
        if file.endswith('.py') or file.endswith('.xml') or file.endswith('.csv'):
            remove_bom(os.path.join(root, file))
