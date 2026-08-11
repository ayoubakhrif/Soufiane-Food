import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Update stes_names logic
old_stes_names = """            stes = self.env['finance2.ste'].sudo().search([])
            stes_names = ", ".join(stes.mapped('name'))"""
            
new_stes_names = """            stes = self.env['finance2.ste'].sudo().search([])
            stes_names = ", ".join([f"{s.name} ({s.raison_social or ''})" for s in stes])"""
content = content.replace(old_stes_names, new_stes_names)

# Update the prompt
old_prompt = """1. "chq": Le numéro du chèque (généralement 7 chiffres, ex: 2102888).
2. "ste": L'abréviation de la société émettrice. Essayez de faire correspondre exactement avec l'une de ces abréviations : {stes_names}. 
   - Soufiane Nuts = SN
   - Soufiane Foods = SF
   - Leader One = LO
   - Pacific Fruit = PF
   - Maruk = MR"""

new_prompt = """1. "chq": Le numéro du chèque (généralement 7 chiffres, ex: 2102888).
2. "ste": La société émettrice. Cherchez la raison sociale inscrite sur le chèque, et comparez avec la liste suivante : {stes_names}. Extrayez l'abréviation correspondante (la valeur avant les parenthèses)."""

prompt_pattern = re.compile(r'1\. "chq": Le num.ro du ch.que.*?- Maruk = MR', re.DOTALL)
content = prompt_pattern.sub(new_prompt, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated raison social logic")
