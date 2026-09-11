import os
import re

filepath = 'custom-addons/tanger_med/views/sutra_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace payment_state widget in all occurrences
old_badge = """<field name="payment_state" widget="badge" decoration-success="payment_state == 'paye'" decoration-danger="payment_state == 'non_paye'"/>"""
new_badge = """<field name="payment_state" widget="badge" decoration-success="payment_state == 'paye'" decoration-warning="payment_state == 'non_paye'" decoration-danger="payment_state == 'sans_facture'"/>"""
content = content.replace(old_badge, new_badge)

# Update form view of sutra.facture
old_sutra_id = """<field name="sutra_id"/>"""
new_sutra_id = """<field name="sutra_id" required="0"/>
                                <field name="dum_provisoire" invisible="sutra_id != False" string="DUM Provisoire (Orpheline)"/>"""
content = content.replace(old_sutra_id, new_sutra_id)

# Add search view for sutra.dossier before the tree view
search_view = """
        <record id="view_sutra_dossier_search" model="ir.ui.view">
            <field name="name">sutra.dossier.search</field>
            <field name="model">sutra.dossier</field>
            <field name="arch" type="xml">
                <search>
                    <field name="name"/>
                    <field name="dum"/>
                    <filter string="Sans Facture" name="sans_facture" domain="[('payment_state', '=', 'sans_facture')]"/>
                    <filter string="Non Payé" name="non_paye" domain="[('payment_state', '=', 'non_paye')]"/>
                    <filter string="Payé" name="paye" domain="[('payment_state', '=', 'paye')]"/>
                </search>
            </field>
        </record>

"""
if 'id="view_sutra_dossier_search"' not in content:
    content = content.replace('<record id="view_sutra_dossier_tree"', search_view + '<record id="view_sutra_dossier_tree"')


# Add Factures Orphelines action and menu at the end
orphans_menu = """
        <record id="action_sutra_facture_orphelines" model="ir.actions.act_window">
            <field name="name">Factures Orphelines</field>
            <field name="res_model">sutra.facture</field>
            <field name="view_mode">tree,form</field>
            <field name="domain">[('sutra_id', '=', False)]</field>
            <field name="context">{}</field>
        </record>
        
        <menuitem id="menu_sutra_facture_orphelines" name="Factures Orphelines" parent="menu_sutra_main" action="action_sutra_facture_orphelines" sequence="16"/>
"""
if 'id="action_sutra_facture_orphelines"' not in content:
    content = content.replace('</data>', orphans_menu + '\n    </data>')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sutra_views.xml")
