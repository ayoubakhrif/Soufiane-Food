import os

base_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2'

# 1. Update cheque.py
cheque_model = os.path.join(base_path, 'models', 'cheque.py')
with open(cheque_model, 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure we only remove the one on cheque model (tracking=True usually)
content = content.replace("    serie_facture = fields.Char(string='Série de facture', tracking=True)\n", "")

with open(cheque_model, 'w', encoding='utf-8') as f:
    f.write(content)

# 2. Update cheque_views.xml
cheque_views = os.path.join(base_path, 'views', 'cheque_views.xml')
with open(cheque_views, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the specific field line. It's right after `<field name="journal"/>` in the cheque group
old_xml = """                            <field name="journal"/>
                            <field name="serie_facture"/>
                        </group>"""
new_xml = """                            <field name="journal"/>
                        </group>"""

content = content.replace(old_xml, new_xml)

with open(cheque_views, 'w', encoding='utf-8') as f:
    f.write(content)

# 3. Update whatsapp_finance_api.py
api_file = os.path.join(base_path, 'controllers', 'whatsapp_finance_api.py')
with open(api_file, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('html_content += f"<td>{c_v2.serie_facture or \'\'}</td>"', 'html_content += "<td>-</td>"')

with open(api_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Removed serie_facture from cheque")
