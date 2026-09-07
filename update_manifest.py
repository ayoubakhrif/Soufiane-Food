import os

manifest_path = 'custom-addons/tanger_med/__manifest__.py'
with open(manifest_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("'security/security.xml',", "'security/security.xml',\n        'data/server_actions.xml',")

with open(manifest_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated __manifest__.py")
