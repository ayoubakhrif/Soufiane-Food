import os

init_path = 'custom-addons/tanger_med/models/__init__.py'
with open(init_path, 'r', encoding='utf-8') as f:
    content = f.read()
if 'sutra_import_batch' not in content:
    content += '\nfrom . import sutra_import_batch\n'
    with open(init_path, 'w', encoding='utf-8') as f:
        f.write(content)

manifest_path = 'custom-addons/tanger_med/__manifest__.py'
with open(manifest_path, 'r', encoding='utf-8') as f:
    content = f.read()
if 'sutra_import_batch_views.xml' not in content:
    content = content.replace("'views/finance2_cheque_inherit_views.xml',", "'views/finance2_cheque_inherit_views.xml',\n        'views/sutra_import_batch_views.xml',")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(content)

csv_path = 'custom-addons/tanger_med/security/ir.model.access.csv'
with open(csv_path, 'a', encoding='utf-8') as f:
    f.write("access_sutra_import_batch_user,access.sutra.import.batch.user,model_sutra_import_batch,finance_2.group_finance2_user,1,1,1,1\n")
    f.write("access_sutra_import_batch_manager,access.sutra.import.batch.manager,model_sutra_import_batch,finance_2.group_finance2_manager,1,1,1,1\n")
    f.write("access_sutra_import_line_user,access.sutra.import.line.user,model_sutra_import_line,finance_2.group_finance2_user,1,1,1,1\n")
    f.write("access_sutra_import_line_manager,access.sutra.import.line.manager,model_sutra_import_line,finance_2.group_finance2_manager,1,1,1,1\n")
