import os
import re

base_dir = r"c:\odoo-repos\Soufiane-Food\custom-addons\stock_casa_field"

# 1. Update Driver Views
master_data_xml = os.path.join(base_dir, 'views', 'casa_field_stock_master_data_views.xml')
with open(master_data_xml, 'r', encoding='utf-8') as f:
    xml_content = f.read()

if '<field name="phone"/>' not in xml_content:
    xml_content = xml_content.replace('<field name="name"/>\n                            <field name="employee_id"/>', '<field name="name"/>\n                            <field name="employee_id"/>\n                            <field name="phone"/>\n                            <field name="password" password="True"/>')
    xml_content = xml_content.replace('<field name="name"/>\n                <field name="employee_id"/>', '<field name="name"/>\n                <field name="employee_id"/>\n                <field name="phone"/>\n                <field name="password"/>')
    with open(master_data_xml, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    print("Updated driver views.")

# 2. Create Agent Model
agent_model_path = os.path.join(base_dir, 'models', 'casa_field_stock_agent.py')
if not os.path.exists(agent_model_path):
    with open(agent_model_path, 'w', encoding='utf-8') as f:
        f.write('''from odoo import models, fields

class CasaStockAgent(models.Model):
    _name = 'casa_field.stock.agent'
    _description = 'Agents de Stock Casa'

    name = fields.Char(string='Nom', required=True)
    phone = fields.Char(string='Téléphone', required=True)
    password = fields.Char(string='Mot de passe', required=True)
    active = fields.Boolean(string='Actif', default=True)
''')
    print("Created Agent model.")

    # Update models/__init__.py
    init_path = os.path.join(base_dir, 'models', '__init__.py')
    with open(init_path, 'a', encoding='utf-8') as f:
        f.write('\nfrom . import casa_field_stock_agent\n')

# 3. Create Agent Views
agent_view_path = os.path.join(base_dir, 'views', 'casa_field_stock_agent_views.xml')
if not os.path.exists(agent_view_path):
    with open(agent_view_path, 'w', encoding='utf-8') as f:
        f.write('''<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_casa_field_stock_agent_tree" model="ir.ui.view">
        <field name="name">casa_field.stock.agent.tree</field>
        <field name="model">casa_field.stock.agent</field>
        <field name="arch" type="xml">
            <tree editable="bottom">
                <field name="name"/>
                <field name="phone"/>
                <field name="password" password="True"/>
                <field name="active"/>
            </tree>
        </field>
    </record>

    <record id="action_casa_field_stock_agent" model="ir.actions.act_window">
        <field name="name">Agents de Stock</field>
        <field name="res_model">casa_field.stock.agent</field>
        <field name="view_mode">tree,form</field>
    </record>
</odoo>
''')
    print("Created Agent views.")

    # Update __manifest__.py
    manifest_path = os.path.join(base_dir, '__manifest__.py')
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = f.read()
    
    if 'casa_field_stock_agent_views.xml' not in manifest:
        manifest = manifest.replace("'views/casa_field_stock_master_data_views.xml',", "'views/casa_field_stock_master_data_views.xml',\n        'views/casa_field_stock_agent_views.xml',")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(manifest)

# 4. Update Menus
menu_xml = os.path.join(base_dir, 'views', 'casa_field_stock_menus.xml')
with open(menu_xml, 'r', encoding='utf-8') as f:
    menu_content = f.read()

if 'action_casa_field_stock_agent' not in menu_content:
    menu_content = menu_content.replace(
        '<menuitem id="menu_casa_field_stock_client" name="Clients" parent="menu_casa_field_stock_master_data" action="action_casa_field_stock_client" sequence="20"/>',
        '<menuitem id="menu_casa_field_stock_client" name="Clients" parent="menu_casa_field_stock_master_data" action="action_casa_field_stock_client" sequence="20"/>\n        <menuitem id="menu_casa_field_stock_agent" name="Agents de Stock" parent="menu_casa_field_stock_master_data" action="action_casa_field_stock_agent" sequence="40"/>'
    )
    with open(menu_xml, 'w', encoding='utf-8') as f:
        f.write(menu_content)
    print("Updated Menus.")

# 5. Fix Login logic in API
api_path = os.path.join(base_dir, 'controllers', 'api_stock.py')
with open(api_path, 'r', encoding='utf-8') as f:
    api_content = f.read()

api_content_new = re.sub(
    r"# On se connecte via le chauffeur.*?'role': 'driver'\}\}\)",
    """agent = request.env['casa_field.stock.agent'].sudo().search([('phone', '=', phone), ('active', '=', True)], limit=1)
        if agent and agent.password == password:
            return self._json_response({'status': 'success', 'agent': {'id': agent.id, 'name': agent.name, 'phone': agent.phone, 'role': 'agent'}})

        driver = request.env['casa_field.stock.driver'].sudo().search([('phone', '=', phone)], limit=1)
        if driver and driver.password == password:
            return self._json_response({'status': 'success', 'agent': {'id': driver.id, 'name': driver.name, 'phone': driver.phone, 'role': 'driver'}})""",
    api_content, flags=re.DOTALL
)

if api_content != api_content_new:
    with open(api_path, 'w', encoding='utf-8') as f:
        f.write(api_content_new)
    print("Updated Login API to support Agents.")
