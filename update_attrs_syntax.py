import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/views/cheque_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    """<field name="date_encaissement" attrs="{'invisible': [('state', 'in', ['brouillon', 'reserve', 'actif'])]}"/>""",
    """<field name="date_encaissement" invisible="state in ('brouillon', 'reserve', 'actif')"/>"""
)

content = content.replace(
    """<field name="montant_encaisse" attrs="{'invisible': [('state', 'in', ['brouillon', 'reserve', 'actif'])]}"/>""",
    """<field name="montant_encaisse" invisible="state in ('brouillon', 'reserve', 'actif')"/>"""
)

content = content.replace(
    """<field name="date_encaissement" attrs="{'readonly': [('state', '=', 'encaisse')]}"/>""",
    """<field name="date_encaissement" readonly="state == 'encaisse'"/>"""
)

content = content.replace(
    """<field name="montant_encaisse" attrs="{'readonly': [('state', '=', 'encaisse')]}" sum="Total Encaissé"/>""",
    """<field name="montant_encaisse" readonly="state == 'encaisse'" sum="Total Encaissé"/>"""
)

content = content.replace(
    """<button name="action_encaisser" type="object" icon="fa-check" string="Encaisser" class="oe_highlight" attrs="{'invisible': [('state', '!=', 'cloture')]}"/>""",
    """<button name="action_encaisser" type="object" icon="fa-check" string="Encaisser" class="oe_highlight" invisible="state != 'cloture'"/>"""
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated xml syntax for Odoo 17")
