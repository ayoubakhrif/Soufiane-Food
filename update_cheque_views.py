import os

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add difference to encaissement tree
old_tree_amount = "<field name=\"montant_encaisse\" readonly=\"state == 'encaisse'\" sum=\"Total Encaiss\xc3\xa9\"/>"
new_tree_amount = """<field name="montant_encaisse" readonly="state == 'encaisse'" sum="Total Encaissé"/>
                <field name="difference" sum="Total Différence" decoration-danger="difference != 0"/>"""
content = content.replace(old_tree_amount, new_tree_amount)

# Add search view at the top, just before the action
search_view = """
    <!-- Vue Recherche : Chèques -->
    <record id="view_finance2_cheque_search" model="ir.ui.view">
        <field name="name">finance2.cheque.search</field>
        <field name="model">finance2.cheque</field>
        <field name="arch" type="xml">
            <search string="Chèques">
                <field name="name"/>
                <field name="ste_id"/>
                <field name="benif_id"/>
                <field name="journal"/>
                <filter string="Différence ≠ 0" name="diff_not_zero" domain="[('difference', '!=', 0)]"/>
                <separator/>
                <filter string="Brouillon" name="brouillon" domain="[('state', '=', 'brouillon')]"/>
                <filter string="Réservés" name="reserve" domain="[('state', '=', 'reserve')]"/>
                <filter string="Clôturés" name="cloture" domain="[('state', '=', 'cloture')]"/>
                <filter string="Encaissés" name="encaisse" domain="[('state', '=', 'encaisse')]"/>
                <group expand="0" string="Regrouper par">
                    <filter string="Date d'encaissement" name="group_date_encaissement" context="{'group_by':'date_encaissement:day'}"/>
                    <filter string="Statut" name="group_state" context="{'group_by':'state'}"/>
                    <filter string="Société" name="group_ste" context="{'group_by':'ste_id'}"/>
                    <filter string="Bénéficiaire" name="group_benif" context="{'group_by':'benif_id'}"/>
                </group>
            </search>
        </field>
    </record>

    <!-- Action Chèques -->
"""
# Replace the first Action to insert search view before it
# Wait, let's insert it before <record id="action_finance2_cheque"
content = content.replace('    <!-- Action Chèques -->', search_view)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated XML views")
