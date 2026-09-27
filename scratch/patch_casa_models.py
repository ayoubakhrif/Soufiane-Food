import os
import re

base_dir = r"c:\odoo-repos\Soufiane-Food\custom-addons\stock_casa_field"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    orig_content = content
    
    if filepath.endswith('.py'):
        # Remove ste_id definition
        content = re.sub(r"^[ \t]*ste_id = fields\..*?$\n", "", content, flags=re.MULTILINE)
        content = re.sub(r"^[ \t]*'ste_id':.*?,$\n", "", content, flags=re.MULTILINE)
        content = re.sub(r"^[ \t]*'default_ste_id':.*?,$\n", "", content, flags=re.MULTILINE)
        
        # Remove garage definition
        # First remove Selection blocks
        content = re.sub(r"^[ \t]*garage = fields\.Selection\(\[.*?\](?:, string='Garage'.*?|\).*?)$\n", "", content, flags=re.MULTILINE | re.DOTALL)
        content = re.sub(r"^[ \t]*garage = fields\..*?$\n", "", content, flags=re.MULTILINE)
        content = re.sub(r"^[ \t]*'garage':.*?,$\n", "", content, flags=re.MULTILINE)
        content = re.sub(r"^[ \t]*'default_garage':.*?,$\n", "", content, flags=re.MULTILINE)
        
        # Remove from domain and read_group
        content = re.sub(r"^[ \t]*\('garage', '=', [^\)]+\),$\n", "", content, flags=re.MULTILINE)
        
        # Remove from GROUP BY in SQL
        content = re.sub(r"m\.garage, ", "", content)
        content = re.sub(r"m\.garage", "", content)
        
        # Remove from forbidden_fields lists
        content = re.sub(r"'garage', ", "", content)
        content = re.sub(r"'ste_id', ", "", content)
        content = re.sub(r"'garage'", "", content)
        
        # In stock_stock SQL view select
        content = re.sub(r"^[ \t]*m\.garage,$\n", "", content, flags=re.MULTILINE)
        
    elif filepath.endswith('.xml'):
        # Remove fields from views
        content = re.sub(r'<field name="ste_id".*?/>\n?', "", content)
        content = re.sub(r'<field name="garage".*?/>\n?', "", content)
        # Handle group by context
        content = re.sub(r'<filter string="Garage" .*? context="\{\'group_by\': \'garage\'\}"/>\n?', "", content)

    if orig_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith(('.py', '.xml')):
            process_file(os.path.join(root, file))
