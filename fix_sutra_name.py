import os

filepath = 'custom-addons/tanger_med/models/sutra.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("vals['name'] = f'SUTRA - {log_entry.name}'", "vals['name'] = f'SUTRA - {log_entry.display_name}'")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sutra.py")
