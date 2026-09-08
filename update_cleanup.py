import os

init_path = 'custom-addons/tanger_med/wizard/__init__.py'
with open(init_path, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace("from . import sutra_import_wizard\n", "")
with open(init_path, 'w', encoding='utf-8') as f:
    f.write(content)

manifest_path = 'custom-addons/tanger_med/__manifest__.py'
with open(manifest_path, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace("'wizard/sutra_import_wizard_views.xml',\n", "")
with open(manifest_path, 'w', encoding='utf-8') as f:
    f.write(content)

csv_path = 'custom-addons/tanger_med/security/ir.model.access.csv'
with open(csv_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
new_lines = [l for l in lines if 'sutra.import.wizard' not in l]
with open(csv_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
