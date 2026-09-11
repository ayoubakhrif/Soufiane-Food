import os

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove the invisible week from sheet
content = content.replace('<field name="week" invisible="1"/>', '')

# 2. Add week under date_emission in Form View
old_date_emission_form = """                            <field name="date_emission"/>"""
new_date_emission_form = """                            <field name="date_emission"/>
                            <field name="week" readonly="1" force_save="1"/>"""
content = content.replace(old_date_emission_form, new_date_emission_form, 1)

# 3. Add week under date_emission in Tree View
old_date_emission_tree = """                <field name="date_emission"/>"""
new_date_emission_tree = """                <field name="date_emission"/>
                <field name="week" optional="show"/>"""
content = content.replace(old_date_emission_tree, new_date_emission_tree, 1)

# Just in case the second one failed because of spaces, we can use regex or another string check
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cheque views with week field")
