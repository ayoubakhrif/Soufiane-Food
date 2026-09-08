import os

filepath = 'custom-addons/tanger_med/views/sutra_import_batch_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '''<button name="action_process" string="Generer les Factures" type="object" class="btn-primary" invisible="state != 'draft'"/>''',
    '''<button name="action_process" string="Generer les Factures" type="object" class="btn-primary"/>'''
)
content = content.replace(
    '''<button name="action_verify" string="Verifier les DUM" type="object" class="btn-secondary" invisible="state != 'draft'"/>''',
    '''<button name="action_verify" string="Verifier les DUM" type="object" class="btn-secondary"/>'''
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated view to make buttons always visible")
