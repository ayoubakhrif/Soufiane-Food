import os

filepath = 'custom-addons/tanger_med/data/server_actions.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_action = """
    <!-- Server Action to Refresh DUM on old SUTRA Dossiers -->
    <record id="action_refresh_sutra_dossier_dum" model="ir.actions.server">
        <field name="name">Rafraichir les DUM</field>
        <field name="model_id" ref="model_sutra_dossier"/>
        <field name="binding_model_id" ref="model_sutra_dossier"/>
        <field name="binding_view_types">list</field>
        <field name="state">code</field>
        <field name="code">
            if records:
                for rec in records:
                    rec._compute_dum()
        </field>
    </record>

</data>"""

content = content.replace('</data>', new_action)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added server action")
