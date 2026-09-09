import os

filepath = 'custom-addons/tanger_med/views/finance2_cheque_inherit_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure we add the field to the view so it can be evaluated in `invisible`
old_xml = """                <xpath expr="//notebook" position="inside">
                    <page string="Factures SUTRA">"""

new_xml = """                <xpath expr="//sheet" position="inside">
                    <field name="is_sutra_benif" invisible="1"/>
                </xpath>
                <xpath expr="//notebook" position="inside">
                    <page string="Factures SUTRA" invisible="not is_sutra_benif">"""

content = content.replace(old_xml, new_xml)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated XML view")
