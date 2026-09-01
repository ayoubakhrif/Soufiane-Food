import os

base_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2'
cheque_views = os.path.join(base_path, 'views', 'cheque_views.xml')

with open(cheque_views, 'r', encoding='utf-8') as f:
    xml_content = f.read()

new_views = """
    <!-- Calendrier -->
    <record id="view_finance2_cheque_calendar" model="ir.ui.view">
        <field name="name">finance2.cheque.calendar</field>
        <field name="model">finance2.cheque</field>
        <field name="arch" type="xml">
            <calendar string="Chèques" date_start="date_emission" date_stop="date_echeance" color="state">
                <field name="name"/>
                <field name="ste_id"/>
                <field name="benif_id"/>
                <field name="amount_total"/>
            </calendar>
        </field>
    </record>

    <!-- Graphique -->
    <record id="view_finance2_cheque_graph" model="ir.ui.view">
        <field name="name">finance2.cheque.graph</field>
        <field name="model">finance2.cheque</field>
        <field name="arch" type="xml">
            <graph string="Analyse des Chèques" type="bar">
                <field name="date_emission" type="row"/>
                <field name="amount_total" type="measure"/>
            </graph>
        </field>
    </record>

    <!-- Tableau Croisé (Pivot) -->
    <record id="view_finance2_cheque_pivot" model="ir.ui.view">
        <field name="name">finance2.cheque.pivot</field>
        <field name="model">finance2.cheque</field>
        <field name="arch" type="xml">
            <pivot string="Analyse des Chèques">
                <field name="date_emission" type="row" interval="month"/>
                <field name="ste_id" type="col"/>
                <field name="amount_total" type="measure"/>
            </pivot>
        </field>
    </record>
"""

if 'finance2.cheque.graph' not in xml_content:
    # Insert before action
    xml_content = xml_content.replace(
        '<record id="action_finance2_cheque"',
        new_views + '\n    <record id="action_finance2_cheque"'
    )
    # Update action view_mode
    xml_content = xml_content.replace(
        '<field name="view_mode">tree,form</field>',
        '<field name="view_mode">tree,form,calendar,graph,pivot</field>'
    )
    # Note: encaissement action might need it too?
    # Actually, encaissement action view_mode is tree,form. Let's just do it for all actions on finance2.cheque except specific ones if needed.
    # Let's replace ONLY the main action's view_mode, or all if safe.
    # Main action is "action_finance2_cheque". We can replace that specific block.

    with open(cheque_views, 'w', encoding='utf-8') as f:
        f.write(xml_content)

print("Views added.")
