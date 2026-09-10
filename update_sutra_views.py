import os

filepath = 'custom-addons/tanger_med/views/sutra_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '<field name="amount_single"/><field name="amount_multiple"/>',
    '<field name="amount_single"/><field name="amount_multiple"/><field name="amount_temsa"/>'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sutra_views.xml")
