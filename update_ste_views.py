import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/views/personne_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add raison_social to the tree view
old_tree = """    <record id="view_finance2_ste_tree" model="ir.ui.view">
        <field name="name">finance2.ste.tree</field>
        <field name="model">finance2.ste</field>
        <field name="arch" type="xml">
            <tree string="Sociétés">
                <field name="name"/>
            </tree>
        </field>
    </record>"""

new_tree_and_form = """    <record id="view_finance2_ste_tree" model="ir.ui.view">
        <field name="name">finance2.ste.tree</field>
        <field name="model">finance2.ste</field>
        <field name="arch" type="xml">
            <tree string="Sociétés">
                <field name="name"/>
                <field name="raison_social"/>
            </tree>
        </field>
    </record>

    <record id="view_finance2_ste_form" model="ir.ui.view">
        <field name="name">finance2.ste.form</field>
        <field name="model">finance2.ste</field>
        <field name="arch" type="xml">
            <form string="Société">
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="raison_social"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>"""

content = content.replace(old_tree, new_tree_and_form)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated personne_views.xml")
