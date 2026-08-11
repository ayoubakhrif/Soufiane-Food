import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the prompt section
new_prompt = """1. "chq": Le numéro du chèque (généralement 7 chiffres, ex: 2102888).
2. "ste": L'abréviation de la société émettrice. Essayez de faire correspondre exactement avec l'une de ces abréviations : {stes_names}. 
   - Soufiane Nuts = SN
   - Soufiane Foods = SF
   - Leader One = LO
   - Pacific Fruit = PF
   - Maruk = MR
3. "date_emission": La date qui se situe sur le cachet en dessous (la première date inscrite), au format YYYY-MM-DD.
4. "personne": La personne écrite sur le cachet (sur la deuxième ligne). Essayez de faire correspondre avec l'un de ces noms : {persos_names}.
5. "journal": Le numéro écrit manuellement en haut. Dans la majorité des cas, on voit un format comme Wxx-Journal (par exemple "W33-12"). Dans ce cas, extrayez uniquement le numéro du journal (ici "12").

Retournez UNIQUEMENT un objet JSON valide, sans markdown.
Exemple:
{{
  "chq": "2102888",
  "ste": "SN",
  "date_emission": "2026-05-18",
  "personne": "Abderzak",
  "journal": "12"
}}"""

prompt_pattern = re.compile(r'1\. "chq": Le num.ro du ch.que.*?personne": "Abderzak"\n\}\}', re.DOTALL)
content = prompt_pattern.sub(new_prompt, content)

# Update the parsing block
old_parsing = """            if perso_record:
                update_vals['personne_id'] = perso_record.id
            if result.get('date_emission'):
                update_vals['date_emission'] = result.get('date_emission')"""

new_parsing = """            if perso_record:
                update_vals['personne_id'] = perso_record.id
            if result.get('date_emission'):
                update_vals['date_emission'] = result.get('date_emission')
            
            raw_journal = str(result.get('journal', ''))
            match = re.search(r'\\d+', raw_journal)
            if match:
                update_vals['journal'] = match.group()"""

content = content.replace(old_parsing, new_parsing)

# Update the success message
old_msg = """f"<p style='margin:4px 0 0;'>Le système a extrait le numéro <b>{final_chq}</b>, la société <b>{ste_code}</b>, la date d'émission <b>{result.get('date_emission', '')}</b> et la personne <b>{perso_name}</b>.</p>\""""
new_msg = """f"<p style='margin:4px 0 0;'>Le système a extrait le numéro <b>{final_chq}</b>, la société <b>{ste_code}</b>, la date d'émission <b>{result.get('date_emission', '')}</b>, la personne <b>{perso_name}</b>, et le journal <b>{update_vals.get('journal', '')}</b>.</p>\""""
msg_pattern = re.compile(r'f"<p style=\'margin:4px 0 0;\'>Le syst.me a extrait le num.ro <b>\{final_chq\}</b>, la soci.t. <b>\{ste_code\}</b>, la date d\'.mission <b>\{result.get\(\'date_emission\', \'\'\)\}</b> et la personne <b>\{perso_name\}</b>.</p>"')
content = msg_pattern.sub(new_msg, content)


with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added journal extraction")
