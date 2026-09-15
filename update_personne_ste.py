import os

filepath = 'custom-addons/finance_2/views/personne_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add ste_id after name
old_line = '<field name="name" string="Chèque"/>'
new_line = '<field name="name" string="Chèque"/>\n                                    <field name="ste_id" string="Société"/>'

content = content.replace(old_line, new_line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated personne_views.xml")
