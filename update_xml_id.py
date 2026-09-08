import os

xml_path = 'custom-addons/tanger_med/data/server_actions.xml'
with open(xml_path, 'r', encoding='utf-8') as f:
    xml_content = f.read()

xml_content = xml_content.replace('id="action_generate_missing_sutra"', 'id="action_generate_missing_sutra_v2"')

with open(xml_path, 'w', encoding='utf-8') as f:
    f.write(xml_content)

print("Updated XML ID")
