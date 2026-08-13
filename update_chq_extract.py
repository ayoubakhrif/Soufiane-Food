import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/controllers/whatsapp_pdf_bot_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Update the prompt in whatsapp_pdf_bot_api.py
old_instruction_1 = """1. Trouvez le numéro de chèque. ATTENTION RÈGLE ABSOLUE : Le chèque se trouve TOUJOURS sur la dernière page du document. Le numéro de chèque est EXACTEMENT composé de 7 chiffres et se trouve TOUJOURS en haut à gauche du chèque (souvent après la mention 'Chèque N°' ou 'N.'). Il ne fait jamais plus de 7 chiffres. Ne le confondez SURTOUT PAS avec les numéros de compte très longs en bas, ni avec le montant du chèque qui se trouve TOUJOURS en haut à droite. S'il y a plusieurs factures ou plusieurs types de frais dans le même document, traitez-les séparément."""

new_instruction_1 = """1. Trouvez les informations du chèque (qui se trouve TOUJOURS sur la dernière page du document) :
   - Le numéro de chèque: EXACTEMENT 7 chiffres, TOUJOURS en haut à gauche. Ne le confondez pas avec le compte ou le montant.
   - Le montant du chèque: C'est le montant total écrit sur le chèque (en haut à droite et en toutes lettres).
   - La date d'échéance du chèque: C'est la date écrite sur le chèque (souvent en bas à droite). Formatez-la OBLIGATOIREMENT en 'YYYY-MM-DD' (ex: 2026-08-15). S'il n'y a pas de date, laissez vide."""

content = content.replace(old_instruction_1, new_instruction_1)

old_json_structure = """- Le JSON doit suivre cette structure exacte :
{
  "chq_number": "1234567",
  "factures": ["""

new_json_structure = """- Le JSON doit suivre cette structure exacte :
{
  "chq_number": "1234567",
  "chq_amount": 10500.50,
  "chq_date": "2026-08-15",
  "factures": ["""

content = content.replace(old_json_structure, new_json_structure)

# Update the python processing logic
old_save_pdf = """        # Save the document PDF on the cheque
        if pdf_base64:
            base_cheque.sudo().write({
                'doc_pdf': pdf_base64,
                'doc_filename': file_name
            })"""

new_save_pdf = """        # Save the document PDF and the extracted cheque details
        update_vals = {}
        if pdf_base64:
            update_vals.update({
                'doc_pdf': pdf_base64,
                'doc_filename': file_name
            })
            
        chq_amount = ai_result.get('chq_amount')
        chq_date = ai_result.get('chq_date')
        
        if chq_amount:
            try:
                update_vals['amount_total'] = float(chq_amount)
            except ValueError:
                pass
                
        if chq_date and len(str(chq_date)) >= 10:
            update_vals['date_echeance'] = str(chq_date)[:10]

        if update_vals:
            base_cheque.sudo().write(update_vals)"""

content = content.replace(old_save_pdf, new_save_pdf)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated whatsapp_pdf_bot_api.py to extract and save cheque date and amount")
