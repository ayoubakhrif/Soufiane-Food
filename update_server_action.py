import os

filepath = 'custom-addons/tanger_med/data/server_actions.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_action = """
    <!-- Server Action to Mark Sutra Factures as Paid in Bulk -->
    <record id="action_mark_sutra_facture_paid" model="ir.actions.server">
        <field name="name">Marquer comme Payé</field>
        <field name="model_id" ref="model_sutra_facture"/>
        <field name="binding_model_id" ref="model_sutra_facture"/>
        <field name="binding_view_types">list</field>
        <field name="state">code</field>
        <field name="code">
            if records:
                records.write({'state': 'paye'})
        </field>
    </record>
"""

if "action_mark_sutra_facture_paid" not in content:
    content = content.replace("</data>", new_action + "\n</data>")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added server action")
