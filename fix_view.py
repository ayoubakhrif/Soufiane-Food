import os

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add week as an invisible field inside the form sheet so it can be used in the header modifier
old_sheet = """                <sheet>
                    <div class="oe_title">"""
new_sheet = """                <sheet>
                    <field name="week" invisible="1"/>
                    <div class="oe_title">"""

content = content.replace(old_sheet, new_sheet)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added week field to view")
