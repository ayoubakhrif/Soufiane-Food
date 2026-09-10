import os
import re

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if "'response': f\"Voici le rapport des chèques{encaisse_label.lower()} pour la semaine *{week_str}*.\" +" in line:
        new_lines.append(line)
        new_lines.append("                                (f\"\\n\\n⚠️ *Journaux manquants ({len(missing_journals)} chqs) :* {', '.join(map(str, missing_journals))}\" if missing_journals else \"\") +\n")
        new_lines.append("                                (f\"\\n\\n❌ *Chq vide absent ({len(chq_vide_missing_journals)} chqs) :* Les journaux des chqs sans pdf de chq vide: {', '.join(sorted(chq_vide_missing_journals))}\" if chq_vide_missing_journals else \"\") +\n")
        new_lines.append("                                (f\"\\n\\n❌ *Documentation absente ({len(doc_missing_journals)} chqs) :* Journaux des chqs sans pdf de documentation: {', '.join(sorted(doc_missing_journals))}\" if doc_missing_journals else \"\"),\n")
        skip = True
        continue
    
    if skip and "'files': [" in line:
        skip = False
        
    if not skip:
        new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Fixed syntax error")
