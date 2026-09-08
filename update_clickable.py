import os

filepath = 'custom-addons/tanger_med/views/sutra_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '''<field name="state" widget="statusbar" statusbar_visible="non_paye,encours,paye"/>''',
    '''<field name="state" widget="statusbar" statusbar_visible="non_paye,encours,paye" options="{'clickable': '1'}"/>'''
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sutra_views.xml to make statusbar clickable")
