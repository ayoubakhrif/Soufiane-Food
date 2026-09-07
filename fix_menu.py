import os

manifest_path = 'custom-addons/tanger_med/__manifest__.py'
with open(manifest_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("'depends': ['base', 'logistique'],", "'depends': ['base', 'logistique', 'finance_2'],")

with open(manifest_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated __manifest__.py")

xml_path = 'custom-addons/tanger_med/views/sutra_views.xml'
with open(xml_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_menu = """        <!-- Main Menu -->
        <menuitem id="menu_sutra_root" name="SUTRA" sequence="60" web_icon="tanger_med,static/description/icon.png"/>
        <menuitem id="menu_sutra_dossiers" name="Dossiers SUTRA" parent="menu_sutra_root" action="action_sutra_dossier" sequence="10"/>"""

new_menu = """        <!-- Main Menu under Finance V2 -->
        <menuitem id="menu_sutra_dossiers" name="SUTRA" parent="finance_2.menu_finance2_root" action="action_sutra_dossier" sequence="50"/>"""

content = content.replace(old_menu, new_menu)

with open(xml_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sutra_views.xml")
