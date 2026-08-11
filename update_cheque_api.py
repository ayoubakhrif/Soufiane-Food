import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_ai_logic = """            api_key = self.env['ir.config_parameter'].sudo().get_param('finance.gemini_api_key')
            if not api_key:
                rec.message_post(body="<div style='color:red;'>Erreur: finance.gemini_api_key est vide ou non configuré.</div>")
                continue

            import requests
            import json
            import re

            pdf_bytes = rec.chq_vide_pdf.decode('utf-8') if isinstance(rec.chq_vide_pdf, bytes) else rec.chq_vide_pdf
            import base64
            try:
                pdf_bytes_decoded = base64.b64decode(pdf_bytes)
            except Exception:
                pdf_bytes_decoded = pdf_bytes # Just in case it's not base64 encoded properly

            stes = self.env['finance2.ste'].sudo().search([])
            stes_names = ", ".join(stes.mapped('name'))
            
            persos = self.env['finance2.personne'].sudo().search([])
            persos_names = ", ".join(persos.mapped('name'))
            
            benifs = self.env['finance2.benif'].sudo().search([])
            benifs_names = ", ".join(benifs.mapped('name'))

            prompt_text = f\"\"\"Vous êtes un assistant financier. Vous recevez un scan d'un chèque vide.
Votre but est d'extraire les informations suivantes.
1. "chq": Le numéro du chèque (généralement 7 chiffres, ex: 2102888).
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
}}\"\"\"

            # 1. Upload the file to Gemini
            upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={api_key}"
            upload_headers = {
                "X-Goog-Upload-Protocol": "raw",
                "X-Goog-Upload-Header-Content-Type": "application/pdf",
                "Content-Type": "application/pdf"
            }
            try:
                upload_resp = requests.post(upload_url, headers=upload_headers, data=pdf_bytes_decoded, timeout=120)
                if upload_resp.status_code != 200:
                    rec.message_post(body=f"<div style='color:red;'>Erreur Gemini Upload: {upload_resp.text[:500]}</div>")
                    continue
                
                file_uri = upload_resp.json().get("file", {}).get("uri")
                if not file_uri:
                    rec.message_post(body="<div style='color:red;'>Impossible de récupérer l'URI Gemini.</div>")
                    continue
            except Exception as e:
                rec.message_post(body=f"<div style='color:red;'>Exception Gemini Upload: {str(e)}</div>")
                continue

            # 2. Call generateContent
            gemini_model = self.env['ir.config_parameter'].sudo().get_param('finance.gemini_model', 'gemini-pro-latest')
            gemini_model = gemini_model.replace('models/', '')
            # Forcer gemini-pro-latest si la valeur est l'ancienne qui crashait
            if gemini_model in ['gemini-1.5-flash-latest', 'gemini-flash-latest', 'gemini-1.5-flash']:
                gemini_model = 'gemini-pro-latest'

            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}"

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt_text},
                            {"fileData": {"mimeType": "application/pdf", "fileUri": file_uri}}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.0,
                    "responseMimeType": "application/json"
                }
            }

            headers = {
                "Content-Type": "application/json"
            }

            try:
                resp = requests.post(gemini_url, headers=headers, json=payload, timeout=120)
                if resp.status_code != 200:
                    rec.message_post(body=f"<div style='color:red;'>Erreur API Gemini ({resp.status_code}): {resp.text[:500]}</div>")
                    continue
                ai_data = resp.json()
            except Exception as e:
                rec.message_post(body=f"<div style='color:red;'>Exception API Gemini: {str(e)}</div>")
                continue

            raw_content = ""
            candidates = ai_data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    raw_content = parts[0].get("text", "")

            if not raw_content:
                rec.message_post(body="<div style='color:red;'>Erreur: Contenu vide retourné par Gemini.</div>")
                continue
                
            clean_content = re.sub(r'^```(json)?', '', raw_content.strip(), flags=re.IGNORECASE)
            clean_content = re.sub(r'```$', '', clean_content.strip()).strip()

            try:
                result = json.loads(clean_content)
            except Exception as e:
                rec.message_post(body=f"<div style='color:red;'>Erreur de lecture JSON: {str(e)} - Contenu: {clean_content[:200]}</div>")
                continue"""

pattern = re.compile(r"            api_key = self\.env\['ir\.config_parameter'\].sudo\(\)\.get_param\('finance\.gemini_api_key'\).*?            try:\s+result = json\.loads\(raw_content\)\s+except Exception as e:.*?                continue", re.DOTALL)

content = pattern.sub(new_ai_logic, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated to use upload API like tresorerie_chq")
