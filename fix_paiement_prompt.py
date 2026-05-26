import os

filepath = r"c:\odoo-repos\Soufiane-Food\custom-addons\tresorerie_chq\models\paiement.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

old_prompt = '''4. "banque": Le nom de la banque visible sur le document. Essayez de faire correspondre avec l'une de ces banques : {bank_names}.
5. "porteur": Le nom de la personne ou société bénéficiaire / porteur (à l'ordre de).'''

new_prompt = '''4. "banque": Le nom de la banque (à lire souvent dans le logo en HAUT à GAUCHE ou au CENTRE du chèque). Essayez de faire correspondre avec l'une de ces banques : {bank_names}.
5. "porteur": Le nom du titulaire du compte / porteur. C'est le nom imprimé situé en BAS au CENTRE, généralement juste en dessous du "Compte n°". NE CHOISISSEZ PAS le nom de l'agence (qui se trouve à gauche sous "Payable à").'''

content = content.replace(old_prompt, new_prompt)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
