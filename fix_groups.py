import os
import glob

module_dir = 'custom-addons/stock_casa_field'

for root, dirs, files in os.walk(module_dir):
    for file in files:
        if file.endswith('.xml'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content.replace('casa_field_stock.group_manager', 'stock_casa_field.group_manager')
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)

print("Replacement complete.")
