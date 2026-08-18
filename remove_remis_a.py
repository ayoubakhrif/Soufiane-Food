import re

# 1. Update cheque.py
filepath_py = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath_py, 'r', encoding='utf-8') as f:
    content_py = f.read()

# Remove the field definition
content_py = re.sub(r"^\s*remis_a_id\s*=\s*fields\.Many2one\('finance2\.personne',\s*string='Remis à',\s*tracking=True\)\n?", "", content_py, flags=re.MULTILINE)

# Remove constraint involving remis_a_id if any. I remember there was a constraint "je veux qu'on ne peut pas emeetre les chqs vers actif que si émis à est rempli"
# Let's search for it
old_actif_constraint = """            if not rec.remis_a_id:
                raise UserError("Veuillez renseigner la personne à qui le chèque a été remis (champ 'Remis à').")"""

content_py = content_py.replace(old_actif_constraint, "")

with open(filepath_py, 'w', encoding='utf-8') as f:
    f.write(content_py)

# 2. Update cheque_views.xml
filepath_xml = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/views/cheque_views.xml'
with open(filepath_xml, 'r', encoding='utf-8') as f:
    content_xml = f.read()

content_xml = re.sub(r"^\s*<field name=\"remis_a_id\".*?/>\n?", "", content_xml, flags=re.MULTILINE)

with open(filepath_xml, 'w', encoding='utf-8') as f:
    f.write(content_xml)

# 3. Update whatsapp_finance_api.py
filepath_api = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath_api, 'r', encoding='utf-8') as f:
    content_api = f.read()

old_api_code = """        if cheque.remis_a_id:
            msg += f"• *Logistique* : Remis à {cheque.remis_a_id.name}\\n\""""

content_api = content_api.replace(old_api_code, "")

with open(filepath_api, 'w', encoding='utf-8') as f:
    f.write(content_api)

print("Removed remis_a_id everywhere")
