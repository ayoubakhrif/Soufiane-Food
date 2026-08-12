import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Update the header
old_header = """                    <field name="is_admin" invisible="1"/>
                    <field name="state" widget="statusbar" statusbar_visible="brouillon,reserve,actif,cloture" options="{'clickable': '1'}" attrs="{'invisible': [('is_admin', '=', False)]}"/>
                    <field name="state" widget="statusbar" statusbar_visible="brouillon,reserve,actif,cloture" attrs="{'invisible': [('is_admin', '=', True)]}"/>"""

new_header = """                    <field name="is_admin" invisible="1"/>
                    <field name="admin_state" widget="statusbar" statusbar_visible="brouillon,reserve,actif,cloture" options="{'clickable': '1'}" attrs="{'invisible': [('is_admin', '=', False)]}"/>
                    <field name="state" widget="statusbar" statusbar_visible="brouillon,reserve,actif,cloture" attrs="{'invisible': [('is_admin', '=', True)]}"/>"""

content = content.replace(old_header, new_header)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cheque_views.xml with admin_state field")
