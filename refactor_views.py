import codecs
import re

with codecs.open('custom-addons/kal3iya_stock/views/kal3iya_stock_master_data_views.xml', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to remove Driver block
pattern = re.compile(r'    <!-- Driver Views -->.*?    <!-- Driver Action -->.*?    </record>\n', re.DOTALL)
new_content = re.sub(pattern, '', content)

with codecs.open('custom-addons/kal3iya_stock/views/kal3iya_stock_master_data_views.xml', 'w', encoding='utf-8') as f:
    f.write(new_content)

driver_views = '''<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Driver Views -->
    <record id="view_kal3iya_stock_driver_tree" model="ir.ui.view">
        <field name="name">kal3iya.stock.driver.tree</field>
        <field name="model">kal3iya.stock.driver</field>
        <field name="arch" type="xml">
            <tree>
                <field name="name"/>
                <field name="employee_id"/>
                <field name="phone"/>
            </tree>
        </field>
    </record>

    <record id="view_kal3iya_stock_driver_form" model="ir.ui.view">
        <field name="name">kal3iya.stock.driver.form</field>
        <field name="model">kal3iya.stock.driver</field>
        <field name="arch" type="xml">
            <form>
                <sheet>
                    <group>
                        <group>
                            <field name="name"/>
                            <field name="employee_id"/>
                            <field name="phone"/>
                            <field name="password" password="True"/>
                        </group>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <!-- Driver Action -->
    <record id="action_kal3iya_stock_driver" model="ir.actions.act_window">
        <field name="name">Chauffeurs</field>
        <field name="res_model">kal3iya.stock.driver</field>
        <field name="view_mode">tree,form</field>
    </record>
</odoo>
'''

with codecs.open('custom-addons/kal3iya_stock/views/kal3iya_stock_driver_views.xml', 'w', encoding='utf-8') as f:
    f.write(driver_views)

