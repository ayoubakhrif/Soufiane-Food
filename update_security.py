import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/security/security.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add admin group
old_group = """        <record id="group_finance2_manager" model="res.groups">
            <field name="name">Responsable</field>
            <field name="category_id" ref="module_category_finance2"/>
            <field name="implied_ids" eval="[(4, ref('group_finance2_user'))]"/>
            <field name="comment">Le responsable a un accès total (clôture, annulation, configuration).</field>
        </record>"""
        
new_group = """        <record id="group_finance2_manager" model="res.groups">
            <field name="name">Responsable</field>
            <field name="category_id" ref="module_category_finance2"/>
            <field name="implied_ids" eval="[(4, ref('group_finance2_user'))]"/>
            <field name="comment">Le responsable a un accès total (clôture, annulation, configuration).</field>
        </record>

        <!-- Groupe : Administrateur (Forçage) -->
        <record id="group_finance2_admin" model="res.groups">
            <field name="name">Administrateur</field>
            <field name="category_id" ref="module_category_finance2"/>
            <field name="implied_ids" eval="[(4, ref('group_finance2_manager'))]"/>
            <field name="comment">L'administrateur a le droit de forcer les états librement.</field>
        </record>"""

content = content.replace(old_group, new_group)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated security.xml")
