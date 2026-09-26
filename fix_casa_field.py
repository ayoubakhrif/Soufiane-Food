import os
import glob

module_dir = 'custom-addons/stock_casa_field'

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace model names and XML IDs to casa_field
    new_content = content.replace('casa.stock', 'casa_field.stock')
    new_content = new_content.replace('casa_stock', 'casa_field_stock')
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

for root, dirs, files in os.walk(module_dir):
    for file in files:
        if file.endswith('.py') or file.endswith('.xml') or file.endswith('.csv'):
            replace_in_file(os.path.join(root, file))

# Rename files
for root, dirs, files in os.walk(module_dir, topdown=False):
    for file in files:
        if 'casa_stock' in file:
            old_path = os.path.join(root, file)
            new_path = os.path.join(root, file.replace('casa_stock', 'casa_field_stock'))
            os.rename(old_path, new_path)

print("Replacement complete.")
