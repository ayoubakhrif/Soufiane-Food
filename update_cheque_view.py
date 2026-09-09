import os
import re

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the inline button
button_to_remove = """<button name="action_annuler_encaissement" type="object" icon="fa-undo" string="Annuler Encaissement" class="btn-danger" invisible="state != 'encaisse'"/>"""
content = content.replace(button_to_remove, '')

# Add the server action at the bottom before </odoo>
server_action = """
    <!-- Server Action to Cancel Encaissement in Bulk -->
    <record id="action_finance2_annuler_encaissement_bulk" model="ir.actions.server">
        <field name="name">Annuler Encaissement</field>
        <field name="model_id" ref="finance_2.model_finance2_cheque"/>
        <field name="binding_model_id" ref="finance_2.model_finance2_cheque"/>
        <field name="binding_view_types">list</field>
        <field name="state">code</field>
        <field name="code">
            if records:
                records.action_annuler_encaissement()
        </field>
    </record>
"""
if "action_finance2_annuler_encaissement_bulk" not in content:
    content = content.replace('</odoo>', server_action + '\n</odoo>')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated XML view")
