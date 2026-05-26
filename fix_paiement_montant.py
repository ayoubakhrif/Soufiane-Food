import os

filepath = r"c:\odoo-repos\Soufiane-Food\custom-addons\tresorerie_chq\models\paiement.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

old_prompt = '''2. "montant": Le montant du {doc_type[:-1]} (uniquement des chiffres, ex: 1500.50).'''

new_prompt = '''2. "montant": Le montant du {doc_type[:-1]} (uniquement des chiffres, ex: 1500.50). ATTENTION : Lisez attentivement le montant écrit en lettres (qui se trouve souvent au milieu du document, en arabe ou en français) et croisez-le avec le montant en chiffres (en haut à droite) pour garantir l'exactitude absolue du montant extrait.'''

content = content.replace(old_prompt, new_prompt)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
