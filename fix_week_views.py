import os
import re

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix form view
content = content.replace("""                            <field name="date_emission"/>
                <field name="week" optional="show"/>
                            <field name="week" readonly="1" force_save="1"/>""", """                            <field name="date_emission"/>
                            <field name="week" readonly="1" force_save="1"/>""")

# Add to tree view
content = content.replace("""                <field name="date_emission"/>
                <field name="date_echeance"/>""", """                <field name="date_emission"/>
                <field name="week" optional="show"/>
                <field name="date_echeance"/>""")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("View fixed")
