import os

filepath = 'custom-addons/tanger_med/views/sutra_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Update tree view
old_tree = """<tree string="Dossiers SUTRA">
                    <field name="name"/>
                    <field name="logistics_id"/>
                    <field name="amount" sum="Total SUTRA"/>
                </tree>"""
new_tree = """<tree string="Dossiers SUTRA">
                    <field name="name"/>
                    <field name="dum"/>
                    <field name="logistics_id"/>
                    <field name="amount" sum="Total SUTRA"/>
                    <field name="payment_state" widget="badge" decoration-success="payment_state == 'paye'" decoration-danger="payment_state == 'non_paye'"/>
                </tree>"""
content = content.replace(old_tree, new_tree)

# Update form view
old_form = """<group>
                            <group>
                                <field name="logistics_id"/>
                                <field name="amount"/>
                            </group>"""
new_form = """<group>
                            <group>
                                <field name="logistics_id"/>
                                <field name="dum"/>
                            </group>
                            <group>
                                <field name="amount"/>
                                <field name="payment_state" widget="badge" decoration-success="payment_state == 'paye'" decoration-danger="payment_state == 'non_paye'"/>
                            </group>"""
content = content.replace(old_form, new_form)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated XML views for sutra.dossier")
