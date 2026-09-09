import os

filepath = 'custom-addons/tanger_med/views/sutra_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace tree definition
old_tree = """<tree editable="bottom">
                    <field name="ste_id"/>
                    <field name="amount"/>
                </tree>"""

new_tree = """<tree>
                    <field name="ste_id"/>
                    <field name="amount"/>
                    <field name="amount_unbilled" sum="Total Non Facture"/>
                    <field name="amount_unpaid" sum="Total A Payer"/>
                    <field name="amount_total_debt" sum="Total Dette SUTRA" style="font-weight: bold;"/>
                </tree>"""

if old_tree in content:
    content = content.replace(old_tree, new_tree)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated tree view")
else:
    print("Could not find the old tree string")
