import os
import re

filepath = 'custom-addons/tanger_med/models/sutra_import_batch.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_search = "entry = self.env['logistique.entry'].search(['|', ('tanger_med_dum', '=', rec.dum), ('dum', '=', rec.dum)], limit=1)"

new_search = """clean_dum = rec.dum.lstrip('0')
            domain = [
                '|', '|', '|',
                ('tanger_med_dum', '=', rec.dum),
                ('dum', '=', rec.dum),
                ('tanger_med_dum', '=', clean_dum),
                ('dum', '=', clean_dum)
            ]
            entry = self.env['logistique.entry'].search(domain, limit=1)"""

if old_search in content:
    content = content.replace(old_search, new_search)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated search domain")
else:
    print("Old search string not found")
