import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_logic = """        if msg_clean == "divers":
            divers_benifs = request.env['finance.benif'].sudo().search([('is_divers', '=', True)])
            if not divers_benifs:
                return {'status': 'not_found', 'message': "Aucun bénéficiaire de type Divers trouvé."}
            
            report_action = request.env['ir.actions.report'].sudo()
            pdf_content, _ = report_action.with_context(encours_only=False)._render_qweb_pdf('finance.action_report_finance_benif_summary', res_ids=divers_benifs.ids)
            import base64
            from odoo import fields
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            return {
                'status': 'success',
                'response': "Voici la fiche récapitulative de tous les bénéficiaires Divers.",
                'file_name': f"Rapport_Divers_{fields.Date.today()}.pdf",
                'pdf_base64': pdf_base64
            }
"""

if 'msg_clean == "divers"' not in content:
    content = content.replace("        if msg_clean in [\"talon\", \"talons\"]:", new_logic + "\n        if msg_clean in [\"talon\", \"talons\"]:")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated API")
