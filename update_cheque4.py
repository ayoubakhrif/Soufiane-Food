import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add benifs_names before the prompt
old_persos_line = """            stes = self.env['finance2.ste'].sudo().search([])
            stes_names = ", ".join(stes.mapped('name'))
            
            persos = self.env['finance2.personne'].sudo().search([])
            persos_names = ", ".join(persos.mapped('name'))"""
            
new_persos_line = """            stes = self.env['finance2.ste'].sudo().search([])
            stes_names = ", ".join(stes.mapped('name'))
            
            persos = self.env['finance2.personne'].sudo().search([])
            persos_names = ", ".join(persos.mapped('name'))
            
            benifs = self.env['finance2.benif'].sudo().search([])
            benifs_names = ", ".join(benifs.mapped('name'))"""
content = content.replace(old_persos_line, new_persos_line)

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
5. "journal": Le numéro écrit manuellement en haut. Il peut être sous forme "Wxx-Journal" (ex: "W33-12", extrayez uniquement "12") ou bien simplement un chiffre écrit seul (ex: "12"). Extrayez uniquement le numéro du journal.
6. "beneficiaire": Le bénéficiaire (à l'ordre de). Essayez de faire correspondre avec l'un de ces noms : {benifs_names}.

Retournez UNIQUEMENT un objet JSON valide, sans markdown.
Exemple:
{{
  "chq": "2102888",
  "ste": "SN",
  "date_emission": "2026-05-18",
  "personne": "Abderzak",
  "journal": "12",
  "beneficiaire": "AFRICONTAINER"
}}"""

prompt_pattern = re.compile(r'1\. "chq": Le num.ro du ch.que.*?"journal": "12"\n\}\}', re.DOTALL)
content = prompt_pattern.sub(new_prompt, content)

# Update the parsing block
old_parsing = """            perso_name = result.get('personne', '')
            perso_record = False
            if perso_name:
                perso_record = self.env['finance2.personne'].search([('name', '=ilike', perso_name)], limit=1)
                if not perso_record:
                    perso_record = self.env['finance2.personne'].search([('name', 'ilike', perso_name)], limit=1)
            
            update_vals = {}"""

new_parsing = """            perso_name = result.get('personne', '')
            perso_record = False
            if perso_name:
                perso_record = self.env['finance2.personne'].search([('name', '=ilike', perso_name)], limit=1)
                if not perso_record:
                    perso_record = self.env['finance2.personne'].search([('name', 'ilike', perso_name)], limit=1)
                    
            benif_name = result.get('beneficiaire', '')
            benif_record = False
            if benif_name:
                benif_record = self.env['finance2.benif'].search([('name', '=ilike', benif_name)], limit=1)
                if not benif_record:
                    benif_record = self.env['finance2.benif'].search([('name', 'ilike', benif_name)], limit=1)
            
            update_vals = {}"""

content = content.replace(old_parsing, new_parsing)

old_parsing_2 = """            if perso_record:
                update_vals['personne_id'] = perso_record.id"""
new_parsing_2 = """            if perso_record:
                update_vals['personne_id'] = perso_record.id
            if benif_record:
                update_vals['benif_id'] = benif_record.id"""
content = content.replace(old_parsing_2, new_parsing_2)


# Update the success message
old_msg = """f"<p style='margin:4px 0 0;'>Le système a extrait le numéro <b>{final_chq}</b>, la société <b>{ste_code}</b>, la date d'émission <b>{result.get('date_emission', '')}</b>, la personne <b>{perso_name}</b>, et le journal <b>{update_vals.get('journal', '')}</b>.</p>\""""
new_msg = """f"<p style='margin:4px 0 0;'>Le système a extrait le numéro <b>{final_chq}</b>, la société <b>{ste_code}</b>, la date d'émission <b>{result.get('date_emission', '')}</b>, la personne <b>{perso_name}</b>, le journal <b>{update_vals.get('journal', '')}</b> et le bénéficiaire <b>{benif_name}</b>.</p>\""""
msg_pattern = re.compile(r'f"<p style=\'margin:4px 0 0;\'>Le syst.me a extrait le num.ro <b>\{final_chq\}</b>, la soci.t. <b>\{ste_code\}</b>, la date d\'.mission <b>\{result.get\(\'date_emission\', \'\'\)\}</b>, la personne <b>\{perso_name\}</b>, et le journal <b>\{update_vals.get\(\'journal\', \'\'\)\}</b>.</p>"')
content = msg_pattern.sub(new_msg, content)


with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added beneficiaire extraction")
