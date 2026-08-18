import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_json = """            try:
                result = json.loads(clean_content)
            except Exception as e:
                rec.message_post(body=f"<div style='color:red;'>Erreur de lecture JSON: {str(e)} - Contenu: {clean_content[:200]}</div>")
                continue"""

new_json = """            try:
                result = json.loads(clean_content)
            except Exception as e:
                import re
                match = re.search(r'\\{.*\\}', clean_content, re.DOTALL)
                if match:
                    try:
                        result = json.loads(match.group(0))
                    except Exception:
                        rec.message_post(body=f"<div style='color:red;'>Erreur de lecture JSON: {str(e)} - Contenu: {clean_content[:200]}</div>")
                        continue
                else:
                    rec.message_post(body=f"<div style='color:red;'>Erreur de lecture JSON: {str(e)} - Contenu: {clean_content[:200]}</div>")
                    continue"""

content = content.replace(old_json, new_json)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated cheque.py json loading")
