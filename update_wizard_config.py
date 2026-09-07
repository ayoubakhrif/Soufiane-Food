import os

init_path = 'custom-addons/tanger_med/__init__.py'
with open(init_path, 'r', encoding='utf-8') as f:
    content = f.read()

if 'from . import wizard' not in content:
    content += '\nfrom . import wizard\n'
    with open(init_path, 'w', encoding='utf-8') as f:
        f.write(content)
print("Updated __init__.py")

manifest_path = 'custom-addons/tanger_med/__manifest__.py'
with open(manifest_path, 'r', encoding='utf-8') as f:
    content = f.read()

if "'wizard/sutra_import_wizard_views.xml'" not in content:
    content = content.replace("'views/sutra_views.xml',", "'views/sutra_views.xml',\n        'wizard/sutra_import_wizard_views.xml',")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(content)
print("Updated __manifest__.py")

csv_path = 'custom-addons/tanger_med/security/ir.model.access.csv'
with open(csv_path, 'a', encoding='utf-8') as f:
    f.write("access_sutra_import_wizard_user,access.sutra.import.wizard.user,model_sutra_import_wizard,finance_2.group_finance2_user,1,1,1,1\n")
    f.write("access_sutra_import_wizard_manager,access.sutra.import.wizard.manager,model_sutra_import_wizard,finance_2.group_finance2_manager,1,1,1,1\n")
print("Updated access rights")

