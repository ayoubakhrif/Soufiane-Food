import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

import re
# Remove the duplicated leftover code
leftover_pattern = r"            \n            report_action = request.env\['ir.actions.report'\].sudo\(\).*?pdf_base64 = base64\.b64encode\(pdf_content\)\.decode\('utf-8'\)\n            \n            return \{\n                'status': 'success',\n                'response': \"Voici la fiche récapitulative de tous les bénéficiaires Divers\.\",\n                'file_name': f\"Rapport_Divers_\{fields\.Date\.today\(\)\}\.pdf\",\n                'pdf_base64': pdf_base64\n            \}"

content = re.sub(leftover_pattern, "", content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed API")
