import os

base_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2'
personne_py = os.path.join(base_path, 'models', 'personne.py')

with open(personne_py, 'r', encoding='utf-8') as f:
    content = f.read()

# Add cheque_ids to finance2.benif
if 'cheque_ids =' not in content:
    content = content.replace(
        "active = fields.Boolean(default=True)",
        "active = fields.Boolean(default=True)\n    cheque_ids = fields.One2many('finance2.cheque', 'benif_id', string='Chèques')"
    )
    with open(personne_py, 'w', encoding='utf-8') as f:
        f.write(content)

# Update personne_views.xml
personne_xml = os.path.join(base_path, 'views', 'personne_views.xml')
with open(personne_xml, 'r', encoding='utf-8') as f:
    xml_content = f.read()

benif_form = """
    <record id="view_finance2_benif_form" model="ir.ui.view">
        <field name="name">finance2.benif.form</field>
        <field name="model">finance2.benif</field>
        <field name="arch" type="xml">
            <form string="Bénéficiaire">
                <sheet>
                    <div class="oe_title">
                        <h1>
                            <field name="name" placeholder="Nom du bénéficiaire"/>
                        </h1>
                    </div>
                    <notebook>
                        <page string="Récapitulatif des Chèques (V2)">
                            <field name="cheque_ids">
                                <tree>
                                    <field name="name"/>
                                    <field name="date_emission"/>
                                    <field name="amount_total" sum="Total"/>
                                    <field name="state" widget="badge"/>
                                </tree>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
        </field>
    </record>
"""

if 'view_finance2_benif_form' not in xml_content:
    # Insert before action
    xml_content = xml_content.replace(
        '<record id="action_finance2_benif"',
        benif_form + '\n    <record id="action_finance2_benif"'
    )
    with open(personne_xml, 'w', encoding='utf-8') as f:
        f.write(xml_content)

print("Beneficiary recap added.")
