import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# I will just replace the literal newlines back to \n
bad_code = """'response': f"Voici le rapport des chèques{encaisse_label.lower()} pour la semaine *{week_str}*." + 
                                (f"

⚠️ *Journaux manquants ({len(missing_journals)} chqs) :* {', '.join(map(str, missing_journals))}" if missing_journals else "") +
                                (f"

❌ *Chq vide absent ({len(chq_vide_missing_journals)} chqs) :* Les journaux des chqs sans pdf de chq vide: {', '.join(sorted(chq_vide_missing_journals))}" if chq_vide_missing_journals else "") +
                                (f"

❌ *Documentation absente ({len(doc_missing_journals)} chqs) :* Journaux des chqs sans pdf de documentation: {', '.join(sorted(doc_missing_journals))}" if doc_missing_journals else ""),"""

# Note the encoding was messed up too. Let me use regex to fix this.
