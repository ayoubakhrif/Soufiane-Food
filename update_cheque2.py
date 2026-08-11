import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the prompt section
old_prompt = """1. "chq": Le numro du chque (gnralement 7 chiffres, ex: 2102888).
2. "ste": L'abrviation de la socit mettrice. Essayez de faire correspondre exactement avec l'une de ces abrviations : {stes_names}. 
   - Soufiane Nuts = SN
   - Soufiane Foods = SF
   - Leader One = LO
   - Pacific Fruit = PF
   - Maruk = MR

Retournez UNIQUEMENT un objet JSON valide, sans markdown.
Exemple:
{{
  "chq": "2102888",
  "ste": "SN"
}}"""

new_prompt = """1. "chq": Le numéro du chèque (généralement 7 chiffres, ex: 2102888).
2. "ste": L'abréviation de la société émettrice. Essayez de faire correspondre exactement avec l'une de ces abréviations : {stes_names}. 
   - Soufiane Nuts = SN
   - Soufiane Foods = SF
   - Leader One = LO
   - Pacific Fruit = PF
   - Maruk = MR
3. "date_emission": La date qui se situe sur le cachet en dessous (la première date inscrite), au format YYYY-MM-DD.
4. "personne": La personne écrite sur le cachet (sur la deuxième ligne). Essayez de faire correspondre avec l'un de ces noms : {persos_names}.

Retournez UNIQUEMENT un objet JSON valide, sans markdown.
Exemple:
{{
  "chq": "2102888",
  "ste": "SN",
  "date_emission": "2026-05-18",
  "personne": "Abderzak"
}}"""

# Note: since reading produced corrupted chars like , I will use regex to find and replace.
prompt_pattern = re.compile(r'1\. "chq": Le num.ro du ch.que.*?"ste": "SN"\n\}\}', re.DOTALL)
content = prompt_pattern.sub(new_prompt, content)

# I also need to add persos_names before the prompt
persos_line = """            stes = self.env['finance2.ste'].sudo().search([])
            stes_names = ", ".join(stes.mapped('name'))"""
            
new_persos_line = """            stes = self.env['finance2.ste'].sudo().search([])
            stes_names = ", ".join(stes.mapped('name'))
            
            persos = self.env['finance2.personne'].sudo().search([])
            persos_names = ", ".join(persos.mapped('name'))"""
content = content.replace(persos_line, new_persos_line)

# Update the parsing block
old_parsing = """            ste_code = result.get('ste', '')
            ste_record = False
            if ste_code:
                ste_record = self.env['finance2.ste'].search([('name', '=ilike', ste_code)], limit=1)
            
            update_vals = {}
            final_chq = result.get('chq')
            final_ste_id = ste_record.id if ste_record else False

            if final_chq:
                update_vals['name'] = final_chq
            if final_ste_id:
                update_vals['ste_id'] = final_ste_id"""

new_parsing = """            ste_code = result.get('ste', '')
            ste_record = False
            if ste_code:
                ste_record = self.env['finance2.ste'].search([('name', '=ilike', ste_code)], limit=1)
                
            perso_name = result.get('personne', '')
            perso_record = False
            if perso_name:
                perso_record = self.env['finance2.personne'].search([('name', '=ilike', perso_name)], limit=1)
                if not perso_record:
                    perso_record = self.env['finance2.personne'].search([('name', 'ilike', perso_name)], limit=1)
            
            update_vals = {}
            final_chq = result.get('chq')
            final_ste_id = ste_record.id if ste_record else False

            if final_chq:
                update_vals['name'] = final_chq
            if final_ste_id:
                update_vals['ste_id'] = final_ste_id
            if perso_record:
                update_vals['personne_id'] = perso_record.id
            if result.get('date_emission'):
                update_vals['date_emission'] = result.get('date_emission')"""
content = content.replace(old_parsing, new_parsing)

# Update the success message
old_msg = """f"<p style='margin:4px 0 0;'>Le syst.me a extrait le num.ro <b>{final_chq}</b> et la soci.t. <b>{ste_code}</b>.</p>\""""
new_msg = """f"<p style='margin:4px 0 0;'>Le système a extrait le numéro <b>{final_chq}</b>, la société <b>{ste_code}</b>, la date d'émission <b>{result.get('date_emission', '')}</b> et la personne <b>{perso_name}</b>.</p>\""""
msg_pattern = re.compile(r'f"<p style=\'margin:4px 0 0;\'>Le syst.me a extrait le num.ro <b>\{final_chq\}</b> et la soci.t. <b>\{ste_code\}</b>.</p>"')
content = msg_pattern.sub(new_msg, content)


with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added date_emission and personne extraction")
