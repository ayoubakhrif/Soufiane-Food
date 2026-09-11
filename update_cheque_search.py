import os

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add searchable week field in the search view
old_search = """                <search string="Chèques">
                    <field name="name"/>
                    <field name="ste_id"/>
                    <field name="benif_id"/>
                    <field name="journal"/>"""
new_search = """                <search string="Chèques">
                    <field name="name"/>
                    <field name="ste_id"/>
                    <field name="benif_id"/>
                    <field name="journal"/>
                    <field name="week"/>"""

# Note: sometimes special characters inside strings can cause mismatch. Let's just use regex.
import re
content = re.sub(
    r'<search string="Chèques">\s*<field name="name"/>', 
    '<search string="Chèques">\n                    <field name="name"/>\n                    <field name="week" string="Semaine (ex: W36)"/>', 
    content
)
# If previous regex didn't match due to encoding of "Chèques", let's use another hook
if '<field name="week" string="Semaine' not in content:
    content = content.replace('<field name="name"/>', '<field name="name"/>\n                    <field name="week" string="Semaine"/>', 1)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cheque_views.xml")
