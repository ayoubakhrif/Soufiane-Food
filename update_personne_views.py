import os

filepath = 'custom-addons/finance_2/views/personne_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the field cheque_ids ending with the new group
old_xml = """                                    <field name="chq_vide_filename" column_invisible="1"/>
                                    <field name="doc_filename" column_invisible="1"/>
                                </tree>
                            </field>"""
new_xml = """                                    <field name="chq_vide_filename" column_invisible="1"/>
                                    <field name="doc_filename" column_invisible="1"/>
                                </tree>
                            </field>
                            <group class="oe_subtotal_footer" name="benif_total">
                                <field name="total_credit"/>
                                <field name="total_encaisse"/>
                                <field name="solde" class="oe_subtotal_footer_separator"/>
                            </group>"""

content = content.replace(old_xml, new_xml)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated personne_views.xml")
