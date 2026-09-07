import os

filepath = 'custom-addons/tanger_med/views/sutra_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_badge = """decoration-success="state == 'paye'" decoration-danger="state == 'non_paye'\""""
new_badge = """decoration-success="state == 'paye'" decoration-warning="state == 'encours'" decoration-danger="state == 'non_paye'\""""
content = content.replace(old_badge, new_badge)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated badge in sutra_views.xml")
