import re

with open('custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix html_content
if "encaisse_label = " not in content:
    content = content.replace('html_content = f"""', 'encaisse_label = " ENCAISSÉS" if only_encaisse else ""\n            html_content = f"""')

# Fix return block using regex to avoid exact character matching issues
pattern = r"'product_name': f\"Ch[^q]+ques Semaine \{week_str\}\",\s*'response': f\"Voici le rapport des ch[^q]+ques pour la semaine \*\{week_str\}\*\.\"(.*?),\s*'files': \[\s*\{\s*'pdf_base64': pdf_base64,\s*'file_name': f\"Cheques_\{week_str\}\.pdf\",\s*'caption': f\"Ch[^q]+ques de la semaine \{week_str\} [^\"]+\"\s*\}\s*\]"

replacement = r"""'product_name': f"Chèques{encaisse_label.title()} Semaine {week_str}",
                    'response': f"Voici le rapport des chèques{encaisse_label.lower()} pour la semaine *{week_str}*."\1,
                    'files': [
                        {
                            'pdf_base64': pdf_base64,
                            'file_name': f"Cheques_{week_str}{'_encaisses' if only_encaisse else ''}.pdf",
                            'caption': f"Chèques{encaisse_label.lower()} de la semaine {week_str} 📅"
                        }
                    ]"""

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('custom-addons/finance_2/controllers/whatsapp_finance_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed variables")
