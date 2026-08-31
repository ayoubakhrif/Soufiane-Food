import os
import re

base_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2'
cheque_xml = os.path.join(base_path, 'views', 'cheque_views.xml')
talon_xml = os.path.join(base_path, 'views', 'talon_views.xml')

with open(cheque_xml, 'r', encoding='utf-8') as f:
    content_chq = f.read()

menu_pattern = r'    <menuitem id="menu_finance2_talons".*?/>\n'
match = re.search(menu_pattern, content_chq)

if match:
    menu_str = match.group(0)
    content_chq = content_chq.replace(menu_str, '')
    
    with open(cheque_xml, 'w', encoding='utf-8') as f:
        f.write(content_chq)
        
    with open(talon_xml, 'r', encoding='utf-8') as f:
        content_tln = f.read()
    
    content_tln = content_tln.replace('</odoo>', menu_str + '</odoo>')
    with open(talon_xml, 'w', encoding='utf-8') as f:
        f.write(content_tln)
    print('Menu moved successfully.')
else:
    print('Menu not found in cheque_views.xml.')
