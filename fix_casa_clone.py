import os
import glob

module_dir = 'custom-addons/stock_casa_field'

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace model names and XML IDs
    new_content = content.replace('kal3iya.stock', 'casa.stock')
    new_content = new_content.replace('kal3iya_stock', 'casa_stock')
    new_content = new_content.replace('Kal3iya', 'Casa')
    new_content = new_content.replace('kal3iya', 'casa')
    
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
        if 'kal3iya' in file:
            old_path = os.path.join(root, file)
            new_path = os.path.join(root, file.replace('kal3iya', 'casa'))
            os.rename(old_path, new_path)

print("Replacement complete.")
