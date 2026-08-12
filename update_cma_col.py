import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/controllers/whatsapp_pdf_bot_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Update CMA Note
old_cma_note = """   (NOTE SPÉCIALE CMA : Pour le bénéficiaire "CMA", les frais de "magasinage" et de "surestarie" apparaissent souvent sur la MÊME facture. Vous DEVEZ OBLIGATOIREMENT suivre ces règles de calcul :
   - Le montant du "magasinage" est la SOMME EXACTE de tous les montants qui se trouvent sous le titre "(L) Terminal full storage at destination".
   - Le montant de la "surestarie" est la SOMME EXACTE de tous les montants qui se trouvent sous le titre "(C) Detention & Demurrage Import Charge", ET CELA INCLUT AUSSI la "Taxe Regionale" (même si elle se trouve sous "Charges Diverses").
   Extrayez ces deux totaux calculés comme DEUX éléments séparés dans votre tableau JSON, l'un avec le type "magasinage" et l'autre avec le type "surestarie")."""

new_cma_note = """   (NOTE SPÉCIALE CMA : Pour le bénéficiaire "CMA", les frais de "magasinage" et de "surestarie" apparaissent souvent sur la MÊME facture. Vous DEVEZ OBLIGATOIREMENT suivre ces règles de calcul :
   - Le montant du "magasinage" est la SOMME EXACTE de tous les montants qui se trouvent sous le titre "(L) Terminal full storage at destination". ATTENTION: Lisez UNIQUEMENT les montants de la colonne "Montant Total".
   - Le montant de la "surestarie" est la SOMME EXACTE de tous les montants qui se trouvent sous le titre "(C) Detention & Demurrage Import Charge". ATTENTION: Lisez UNIQUEMENT les montants de la colonne "Montant Total". CELA INCLUT AUSSI la "Taxe Regionale" (qui se trouve sous "Charges Diverses").
   Extrayez ces deux totaux calculés comme DEUX éléments séparés dans votre tableau JSON, l'un avec le type "magasinage" et l'autre avec le type "surestarie")."""
content = content.replace(old_cma_note, new_cma_note)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated CMA rules to specify Montant Total column")
