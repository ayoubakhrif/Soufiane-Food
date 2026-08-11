import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/controllers/whatsapp_pdf_bot_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = """        # 5. Find or Create the Cheque in finance_2
        domain = [('name', '=', chq_number)]
        base_cheque = request.env['finance2.cheque'].sudo().search(domain, limit=1)

        if not base_cheque:
            base_cheque = request.env['finance2.cheque'].sudo().create({
                'name': chq_number,
                'state': 'brouillon'
            })"""

new_logic = """        # 5. Find the Cheque in finance_2
        domain = [('name', '=', chq_number)]
        base_cheque = request.env['finance2.cheque'].sudo().search(domain, limit=1)

        if not base_cheque:
            return {'status': 'error', 'message': f"❌ *Erreur:* Le chèque {chq_number} n'existe pas dans Odoo. Vous devez d'abord créer le chèque vide."}
            
        if base_cheque.state != 'actif':
            return {'status': 'error', 'message': f"❌ *Erreur:* Le chèque {chq_number} a été trouvé mais il est à l'état '{base_cheque.state}'. Il doit être à l'état 'actif' pour pouvoir recevoir des répartitions."}"""

content = content.replace(old_logic, new_logic)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated bot logic to check for actif state")
