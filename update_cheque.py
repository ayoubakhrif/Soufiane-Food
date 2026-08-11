import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove required=True from name and ste_id
content = content.replace(
    "name = fields.Char(string='N° Chèque', required=True, tracking=True)",
    "name = fields.Char(string='N° Chèque', required=False, tracking=True)"
)
content = content.replace(
    "ste_id = fields.Many2one('finance2.ste', string='Société', required=True, tracking=True)",
    "ste_id = fields.Many2one('finance2.ste', string='Société', required=False, tracking=True)"
)

# 2. Add the create/write methods and the AI extraction logic
ai_logic = """
    @api.model_create_multi
    def create(self, vals_list):
        records = super(Finance2Cheque, self).create(vals_list)
        for rec in records:
            if rec.chq_vide_pdf and not rec.name:
                rec._extract_empty_cheque_data()
        return records

    def write(self, vals):
        res = super(Finance2Cheque, self).write(vals)
        if 'chq_vide_pdf' in vals and vals['chq_vide_pdf']:
            for rec in self:
                if not rec.name:
                    rec._extract_empty_cheque_data()
        return res

    def _extract_empty_cheque_data(self):
        for rec in self:
            if not rec.chq_vide_pdf:
                continue

            api_key = self.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
            if not api_key:
                continue

            import requests
            import json

            pdf_b64 = rec.chq_vide_pdf.decode('utf-8') if isinstance(rec.chq_vide_pdf, bytes) else rec.chq_vide_pdf
            
            stes = self.env['finance2.ste'].sudo().search([])
            stes_names = ", ".join(stes.mapped('name'))

            prompt_text = f\"\"\"Vous êtes un assistant financier. Vous recevez un scan d'un chèque vide.
Votre but est d'extraire les informations suivantes.
1. "chq": Le numéro du chèque (généralement 7 chiffres, ex: 2102888).
2. "ste": L'abréviation de la société émettrice. Essayez de faire correspondre exactement avec l'une de ces abréviations : {stes_names}. 
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
}}\"\"\"

            payload = {
                "model": "gpt-4o",
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_file",
                                "filename": "cheque.pdf",
                                "file_data": f"data:application/pdf;base64,{pdf_b64}"
                            },
                            {
                                "type": "input_text",
                                "text": prompt_text
                            }
                        ]
                    }
                ],
                "text": {
                    "format": {
                        "type": "json_object"
                    }
                },
                "temperature": 0.0,
                "max_output_tokens": 800
            }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            try:
                resp = requests.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=60)
                if resp.status_code != 200:
                    continue
                ai_data = resp.json()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error AI extract cheque_vide: {str(e)}")
                continue

            raw_content = ""
            for output_item in ai_data.get("output", []):
                for content_item in output_item.get("content", []):
                    if content_item.get("type") == "output_text":
                        raw_content = content_item.get("text", "")
                        break

            if not raw_content:
                continue

            try:
                result = json.loads(raw_content)
            except Exception:
                continue

            ste_code = result.get('ste', '')
            ste_record = False
            if ste_code:
                ste_record = self.env['finance2.ste'].search([('name', '=ilike', ste_code)], limit=1)
            
            update_vals = {}
            final_chq = result.get('chq')
            final_ste_id = ste_record.id if ste_record else False

            if final_chq:
                update_vals['name'] = final_chq
            if final_ste_id:
                update_vals['ste_id'] = final_ste_id
            
            if update_vals:
                rec.sudo().write(update_vals)

            if not final_ste_id or not final_chq:
                from markupsafe import Markup
                rec.message_post(body=Markup(
                    "<div style='border-left:4px solid #ffc107;padding:8px 12px;background:#fff8e1;border-radius:4px;'>"
                    "<span style='color:#ffc107;font-size:15px;'><i class='fa fa-exclamation-triangle'></i>&nbsp;<b>IA : Extraction incomplète</b></span>"
                    f"<p style='margin:4px 0 0;'>L'IA n'a pas pu identifier le numéro de chèque ou la société ({ste_code}). Veuillez remplir ces champs manuellement.</p>"
                    "</div>"
                ))
            else:
                from markupsafe import Markup
                rec.message_post(body=Markup(
                    "<div style='border-left:4px solid #007bff;padding:8px 12px;background:#f8f9fa;border-radius:4px;'>"
                    "<span style='color:#007bff;font-size:15px;'><i class='fa fa-robot'></i>&nbsp;<b>IA : Chèque identifié</b></span>"
                    f"<p style='margin:4px 0 0;'>Le système a extrait le numéro <b>{final_chq}</b> et la société <b>{ste_code}</b>.</p>"
                    "</div>"
                ))

"""

# Replace the old create method with the new logic
start_idx = content.find("    @api.model\n    def create(self, vals):")
end_idx = content.find("    def action_confirmer(self):")

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + ai_logic + content[end_idx:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cheque.py")
