import os
import re

filepath = 'custom-addons/tanger_med/data/server_actions.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to remove the specific server action block
pattern = r'\s*<!-- Server Action to Refresh DUM on old SUTRA Dossiers -->\s*<record id="action_refresh_sutra_dossier_dum" model="ir\.actions\.server">.*?</record>'

new_content = re.sub(pattern, '', content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Removed server action")
