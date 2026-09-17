import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_logic = """        if msg_clean == "divers":
            divers_v2 = request.env['finance2.benif'].sudo().search([('is_divers', '=', True)])
            if not divers_v2:
                return {'status': 'not_found', 'message': "Aucun bénéficiaire de type Divers trouvé dans Finance V2."}
            
            report_action = request.env['ir.actions.report'].sudo()
            pdf_content, _ = report_action._render_qweb_pdf('finance_2.action_report_finance2_divers_summary', res_ids=divers_v2.ids)
            
            import base64
            from odoo import fields
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            return {
                'status': 'success',
                'response': "Voici le tableau récapitulatif DIVERS (Finance V2).",
                'file_name': f"DIVERS_{fields.Date.today()}.pdf",
                'pdf_base64': pdf_base64
            }
"""

import re
content = re.sub(r'        if msg_clean == "divers":.*?            return \{.*?\}', new_logic.strip('\n'), content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated API to use new V2 report")
