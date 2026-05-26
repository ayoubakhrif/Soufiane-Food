import os

filepath = r"c:\odoo-repos\Soufiane-Food\custom-addons\tresorerie_chq\models\paiement.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

old_prompt = '''4. "banque": Le nom de la banque visible sur le document. Essayez de faire correspondre avec l'une de ces banques : {bank_names}.

Exemple de réponse attendue:
{{
  "items": [
    {{
      "numero": "2102888",
      "montant": 18746.43,
      "date_echeance": "2026-05-16",
      "banque": "Attijariwafa Bank"
    }}
  ]
}}"""'''

new_prompt = '''4. "banque": Le nom de la banque visible sur le document. Essayez de faire correspondre avec l'une de ces banques : {bank_names}.
5. "porteur": Le nom de la personne ou société bénéficiaire / porteur (à l'ordre de).

Exemple de réponse attendue:
{{
  "items": [
    {{
      "numero": "2102888",
      "montant": 18746.43,
      "date_echeance": "2026-05-16",
      "banque": "Attijariwafa Bank",
      "porteur": "Ali Yassine"
    }}
  ]
}}"""'''

old_loop = '''            vals = {
                'note': item.get('numero', ''),
                'amount': float(item.get('montant') or 0.0),
                'bank_id': bank_id,
            }'''

new_loop = '''            owner_id = False
            owner_name = item.get('porteur', '')
            if owner_name:
                owner_record = self.env['tresorerie_chq.effets.owner'].search([('name', '=ilike', owner_name)], limit=1)
                if not owner_record:
                    owner_record = self.env['tresorerie_chq.effets.owner'].create({'name': owner_name})
                owner_id = owner_record.id

            vals = {
                'note': item.get('numero', ''),
                'amount': float(item.get('montant') or 0.0),
                'bank_id': bank_id,
                'owner_id': owner_id,
            }'''

content = content.replace(old_prompt, new_prompt)
content = content.replace(old_loop, new_loop)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
