import os

filepath = 'custom-addons/tanger_med/models/sutra_import_batch.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_domain = """            domain = [
                '|', '|', '|',
                ('tanger_med_dum', '=', rec.dum),
                ('dum', '=', rec.dum),
                ('tanger_med_dum', '=', clean_dum),
                ('dum', '=', clean_dum)
            ]"""

new_domain = """            domain = [
                '|',
                ('tanger_med_dum', '=', rec.dum),
                ('tanger_med_dum', '=', clean_dum)
            ]
            if 'dum' in self.env['logistique.entry']._fields:
                domain = ['|', '|', '|', ('tanger_med_dum', '=', rec.dum), ('dum', '=', rec.dum), ('tanger_med_dum', '=', clean_dum), ('dum', '=', clean_dum)]"""

content = content.replace(old_domain, new_domain)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated search domain")
