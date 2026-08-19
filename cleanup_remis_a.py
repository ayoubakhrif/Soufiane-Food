import re

filepath_py = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath_py, 'r', encoding='utf-8') as f:
    content_py = f.read()

# Remove rec.remis_a_id = False
content_py = re.sub(r"^\s*rec\.remis_a_id\s*=\s*False\n?", "", content_py, flags=re.MULTILINE)

# Remove the check in action_mettre_actif
old_check = """        for rec in self:
            if not rec.remis_a_id:
                raise UserError("Vous devez renseigner le champ 'Remis à' avant de passer le chèque à l'état Actif.")
            rec.state = 'actif'"""

new_check = """        for rec in self:
            rec.state = 'actif'"""

content_py = content_py.replace(old_check, new_check)

with open(filepath_py, 'w', encoding='utf-8') as f:
    f.write(content_py)

print("Cleaned up remaining remis_a_id references")
