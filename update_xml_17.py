import os
import re

filepath = 'custom-addons/tanger_med/views/sutra_import_batch_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace attrs
content = content.replace('''attrs="{'readonly': [('state', '=', 'done')]}"''', '''readonly="state == 'done'"''')

# Replace states on buttons
content = content.replace('''states="draft"''', '''invisible="state != 'draft'"''')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sutra_import_batch_views.xml")
