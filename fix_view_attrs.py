import os

filepath = 'custom-addons/tanger_med/views/sutra_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix form view
content = content.replace(
    '<field name="amount_total_debt" widget="monetary" style="color: #dc3545;"/>',
    '<field name="amount_total_debt" widget="monetary" class="text-danger"/>'
)

# Fix tree view
content = content.replace(
    '<field name="amount_total_debt" sum="Total Dette SUTRA" style="font-weight: bold;"/>',
    '<field name="amount_total_debt" sum="Total Dette SUTRA" decoration-bf="1" decoration-danger="1"/>'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed view attributes")
