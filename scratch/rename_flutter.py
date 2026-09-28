import os

base_dir = r"c:\odoo-repos\Soufiane-Food\gestion_stock_app_casa"

def replace_in_file(filepath, old_str, new_str):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    if old_str in content:
        new_content = content.replace(old_str, new_str)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root, dirs, files in os.walk(base_dir):
    # skip .git or build folders if any
    if '.git' in root or 'build' in root or '.dart_tool' in root:
        continue
    for file in files:
        if file.endswith(('.dart', '.html', '.json', '.xml', '.plist')):
            filepath = os.path.join(root, file)
            replace_in_file(filepath, "Kal3iya Stock", "Stock Casa")
            replace_in_file(filepath, "gestion_stock_app", "Stock Casa")

