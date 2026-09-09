import os
import re

filepath = 'custom-addons/tanger_med/views/sutra_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace in tree view
content = content.replace(
    '<field name="amount"/>',
    '<field name="amount_single"/><field name="amount_multiple"/>'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated XML view")
