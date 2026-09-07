import os

manifest_path = 'custom-addons/tanger_med/__manifest__.py'
with open(manifest_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_views = """        'views/finance2_cheque_inherit_views.xml',
        'wizard/sutra_facture_pay_wizard_views.xml',"""

if "'wizard/sutra_facture_pay_wizard_views.xml'" not in content:
    content = content.replace("'wizard/sutra_import_wizard_views.xml',", "'wizard/sutra_import_wizard_views.xml',\n" + new_views)
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(content)
print("Updated __manifest__.py")

csv_path = 'custom-addons/tanger_med/security/ir.model.access.csv'
with open(csv_path, 'a', encoding='utf-8') as f:
    f.write("access_sutra_facture_pay_wizard_user,access.sutra.facture.pay.wizard.user,model_sutra_facture_pay_wizard,finance_2.group_finance2_user,1,1,1,1\n")
    f.write("access_sutra_facture_pay_wizard_manager,access.sutra.facture.pay.wizard.manager,model_sutra_facture_pay_wizard,finance_2.group_finance2_manager,1,1,1,1\n")
print("Updated access rights")

# Also need to create a global list view for SUTRA factures
sutra_views_path = 'custom-addons/tanger_med/views/sutra_views.xml'
with open(sutra_views_path, 'r', encoding='utf-8') as f:
    sutra_views = f.read()

factures_xml = """        <!-- Factures SUTRA Global Tree View -->
        <record id="view_sutra_facture_tree_global" model="ir.ui.view">
            <field name="name">sutra.facture.tree.global</field>
            <field name="model">sutra.facture</field>
            <field name="arch" type="xml">
                <tree string="Factures a payer" create="0">
                    <field name="sutra_id"/>
                    <field name="name"/>
                    <field name="date"/>
                    <field name="amount" sum="Total"/>
                    <field name="state" widget="badge" decoration-success="state == 'paye'" decoration-warning="state == 'encours'" decoration-danger="state == 'non_paye'"/>
                </tree>
            </field>
        </record>

        <record id="action_sutra_facture_global" model="ir.actions.act_window">
            <field name="name">Factures a payer</field>
            <field name="res_model">sutra.facture</field>
            <field name="view_mode">tree,form</field>
            <field name="domain">[('state', '=', 'non_paye')]</field>
            <field name="context">{}</field>
        </record>

        <menuitem id="menu_sutra_facture_global" name="Factures a payer" parent="menu_sutra_main" action="action_sutra_facture_global" sequence="15"/>
"""

if 'view_sutra_facture_tree_global' not in sutra_views:
    sutra_views = sutra_views.replace('</data>', factures_xml + '\n    </data>')
    with open(sutra_views_path, 'w', encoding='utf-8') as f:
        f.write(sutra_views)
print("Updated sutra_views.xml with global facture view")
