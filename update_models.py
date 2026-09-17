import os

filepath = 'custom-addons/finance/models/finance_benif.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

if "is_divers = fields.Boolean(" not in content:
    content = content.replace("name = fields.Char(string='B", "is_divers = fields.Boolean(string='Divers', default=False)\n    name = fields.Char(string='B")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

filepath_view = 'custom-addons/finance/views/benif_view.xml'
if os.path.exists(filepath_view):
    with open(filepath_view, 'r', encoding='utf-8') as f:
        content_view = f.read()
    if 'name="is_divers"' not in content_view:
        content_view = content_view.replace('<field name="name"/>', '<field name="name"/>\n                            <field name="is_divers"/>')
    with open(filepath_view, 'w', encoding='utf-8') as f:
        f.write(content_view)

filepath_personne = 'custom-addons/finance_2/models/personne.py'
with open(filepath_personne, 'r', encoding='utf-8') as f:
    content = f.read()
if "is_divers = fields.Boolean(" not in content:
    content = content.replace("name = fields.Char(string='Nom du b", "is_divers = fields.Boolean(string='Divers', default=False)\n    name = fields.Char(string='Nom du b")
with open(filepath_personne, 'w', encoding='utf-8') as f:
    f.write(content)

filepath_personne_view = 'custom-addons/finance_2/views/personne_views.xml'
with open(filepath_personne_view, 'r', encoding='utf-8') as f:
    content_view = f.read()
if 'name="is_divers"' not in content_view:
    content_view = content_view.replace('<field name="name" placeholder=', '<field name="is_divers"/>\n                            <field name="name" placeholder=')
with open(filepath_personne_view, 'w', encoding='utf-8') as f:
    f.write(content_view)

print("Updated models and views for is_divers")
