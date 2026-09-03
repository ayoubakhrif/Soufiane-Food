import os

file_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2\controllers\whatsapp_pdf_bot_api.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Inject STEs list into the prompt setup
old_setup = """        prompt_text = prompt_text.replace("[IMPORT_LIST]", import_list_str)
        prompt_text = prompt_text.replace("[DIVERS_LIST]", divers_list_str)
        prompt_text = prompt_text.replace("[FEEDBACK]", feedback_instruction)"""

new_setup = """        stes = request.env['finance2.ste'].sudo().search([])
        stes_names = ", ".join([f"{s.name} ({s.raison_social or ''})" for s in stes])
        
        prompt_text = prompt_text.replace("[IMPORT_LIST]", import_list_str)
        prompt_text = prompt_text.replace("[DIVERS_LIST]", divers_list_str)
        prompt_text = prompt_text.replace("[FEEDBACK]", feedback_instruction)
        prompt_text = prompt_text.replace("[STES_LIST]", stes_names)"""

content = content.replace(old_setup, new_setup)

# 2. Update the prompt to ask for the company
old_prompt_info = """   1. Trouvez les informations du chèque (qui se trouve TOUJOURS sur la dernière page du document) :
     - Le numéro de chèque: EXACTEMENT 7 chiffres, TOUJOURS en haut à gauche. Ne le confondez pas avec le compte ou le montant.
     - Le montant du chèque: C'est le montant total écrit sur le chèque (en haut à droite et en toutes lettres).
     - La date d'échéance du chèque: C'est la date écrite sur le chèque (souvent en bas à droite). Formatez-la OBLIGATOIREMENT en 'YYYY-MM-DD' (ex: 2026-08-15). S'il n'y a pas de date, laissez vide."""

new_prompt_info = """   1. Trouvez les informations du chèque (qui se trouve TOUJOURS sur la dernière page du document) :
     - Le numéro de chèque: EXACTEMENT 7 chiffres, TOUJOURS en haut à gauche. Ne le confondez pas avec le compte ou le montant.
     - La société du chèque: Cherchez la raison sociale inscrite sur le chèque, et comparez avec la liste suivante : [STES_LIST]. Extrayez l'abréviation correspondante (la valeur avant les parenthèses).
     - Le montant du chèque: C'est le montant total écrit sur le chèque (en haut à droite et en toutes lettres).
     - La date d'échéance du chèque: C'est la date écrite sur le chèque (souvent en bas à droite). Formatez-la OBLIGATOIREMENT en 'YYYY-MM-DD' (ex: 2026-08-15). S'il n'y a pas de date, laissez vide."""

content = content.replace(old_prompt_info, new_prompt_info)

# 3. Update JSON schema
old_json_schema = """  {
    "chq_number": "1234567",
    "chq_amount": 10500.50,
    "chq_date": "2026-08-15","""

new_json_schema = """  {
    "chq_number": "1234567",
    "chq_ste": "SN",
    "chq_amount": 10500.50,
    "chq_date": "2026-08-15","""

content = content.replace(old_json_schema, new_json_schema)

# 4. Update the search logic
old_search_logic = """        chq_amount_ai = ai_result.get('chq_amount', 0.0)
        chq_date_ai = ai_result.get('chq_date', '')

        # Fallback regex for cheque number if AI completely fails
        if not chq_number and ai_result.get('_raw_json'):
            match = re.search(r'"chq_number"\s*:\s*"(\d{7})"', ai_result.get('_raw_json'))
            if match:
                chq_number = match.group(1)

        if not chq_number:
            return {'status': 'error', 'message': "🚫 *Erreur:* L'IA n'a pas pu identifier le numéro de chèque ni dans le PDF ni dans le nom du fichier (7 chiffres)."}
        
        if not factures:
            return {'status': 'error', 'message': "🚫 *Erreur:* L'IA n'a pas trouvé de factures valides dans le PDF."}

        # 5. Find the Cheque in finance_2
        domain = [('name', '=', chq_number)]
        base_cheque = request.env['finance2.cheque'].sudo().search(domain, limit=1)

        if not base_cheque:"""

new_search_logic = """        chq_ste_ai = ai_result.get('chq_ste', '')
        chq_amount_ai = ai_result.get('chq_amount', 0.0)
        chq_date_ai = ai_result.get('chq_date', '')

        # Fallback regex for cheque number if AI completely fails
        if not chq_number and ai_result.get('_raw_json'):
            match = re.search(r'"chq_number"\s*:\s*"(\d{7})"', ai_result.get('_raw_json'))
            if match:
                chq_number = match.group(1)

        if not chq_number:
            return {'status': 'error', 'message': "🚫 *Erreur:* L'IA n'a pas pu identifier le numéro de chèque ni dans le PDF ni dans le nom du fichier (7 chiffres)."}
        
        if not factures:
            return {'status': 'error', 'message': "🚫 *Erreur:* L'IA n'a pas trouvé de factures valides dans le PDF."}

        # 5. Find the Cheque in finance_2
        domain = [('name', '=', chq_number)]
        if chq_ste_ai:
            domain.append(('ste_id.name', 'ilike', chq_ste_ai))
            
        # Order by state so 'actif' comes first if there's any weird duplicates left
        base_cheques = request.env['finance2.cheque'].sudo().search(domain)
        base_cheque = False
        
        if base_cheques:
            # Prioritize actif cheques
            actifs = base_cheques.filtered(lambda c: c.state == 'actif')
            if actifs:
                base_cheque = actifs[0]
            else:
                base_cheque = base_cheques[0]

        if not base_cheque:"""

content = content.replace(old_search_logic, new_search_logic)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated whatsapp_pdf_bot_api.py properly")
