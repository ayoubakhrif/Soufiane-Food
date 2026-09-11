import os

filepath = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add group by week in search view
old_group = """<group expand="0" string="Regrouper par">
                    <filter string="Date d'encaissement" name="group_date_encaissement" context="{'group_by':'date_encaissement:day'}"/>"""
new_group = """<group expand="0" string="Regrouper par">
                    <filter string="Semaine d'encaissement" name="group_semaine_encaissement" context="{'group_by':'date_encaissement:week'}"/>
                    <filter string="Semaine d'émission" name="group_semaine_emission" context="{'group_by':'date_emission:week'}"/>
                    <filter string="Date d'encaissement" name="group_date_encaissement" context="{'group_by':'date_encaissement:day'}"/>"""
content = content.replace(old_group, new_group)

# 2. Add Server Action
server_action = """
    <record id="action_finance2_assign_talon" model="ir.actions.server">
        <field name="name">Associer au Talon</field>
        <field name="model_id" ref="model_finance2_cheque"/>
        <field name="binding_model_id" ref="model_finance2_cheque"/>
        <field name="binding_view_types">list</field>
        <field name="state">code</field>
        <field name="code">
for record in records:
    if record.name and record.ste_id:
        talon = record._find_matching_talon(record.name, record.ste_id.id)
        if talon:
            record.write({'talon_id': talon.id})
        </field>
    </record>

    <!-- Vue Recherche : Chèques -->"""
if 'action_finance2_assign_talon' not in content:
    content = content.replace('<!-- Vue Recherche : Chèques -->', server_action)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cheque_views.xml")
