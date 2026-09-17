import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_logic = """        if msg_clean == "divers":
            # Search in V2 directly
            divers_v2 = request.env['finance2.benif'].sudo().search([('is_divers', '=', True)])
            if not divers_v2:
                return {'status': 'not_found', 'message': "Aucun bénéficiaire de type Divers trouvé dans Finance V2."}
            
            # Map to V1 to leverage the global report that aggregates V1 + V2 cheques
            v1_ids = []
            for b in divers_v2:
                v1_b = request.env['finance.benif'].sudo().search([('name', '=', b.name)], limit=1)
                if not v1_b:
                    v1_b = request.env['finance.benif'].sudo().create({'name': b.name, 'is_divers': True})
                v1_ids.append(v1_b.id)
                
            report_action = request.env['ir.actions.report'].sudo()
            pdf_content, _ = report_action.with_context(encours_only=False)._render_qweb_pdf('finance.action_report_finance_benif_summary', res_ids=v1_ids)
            
            import base64
            from odoo import fields
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            return {
                'status': 'success',
                'response': "Voici la fiche récapitulative de tous les bénéficiaires Divers (Lecture depuis V2).",
                'file_name': f"Rapport_Divers_{fields.Date.today()}.pdf",
                'pdf_base64': pdf_base64
            }
"""

if 'msg_clean == "divers"' in content:
    # replace the old divers logic
    import re
    content = re.sub(r'        if msg_clean == "divers":.*?            return \{.*?\}', new_logic.strip('\n'), content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated API for Divers")
