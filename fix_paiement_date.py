import os

filepath = r"c:\odoo-repos\Soufiane-Food\custom-addons\tresorerie_chq\models\paiement.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

old_vals = '''            vals = {
                'note': item.get('numero', ''),
                'amount': float(item.get('montant') or 0.0),
                'bank_id': bank_id,
                'owner_id': owner_id,
            }'''

new_vals = '''            vals = {
                'note': item.get('numero', ''),
                'amount': float(item.get('montant') or 0.0),
                'bank_id': bank_id,
                'owner_id': owner_id,
            }
            if self.reception_date:
                vals['reception_date'] = self.reception_date'''

content = content.replace(old_vals, new_vals)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
