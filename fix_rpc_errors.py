import os

# 1. Fix wizard code
filepath_wizard = 'custom-addons/tanger_med/wizard/sutra_facture_pay_wizard.py'
with open(filepath_wizard, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("'dossier_name': 'Paiement SUTRA Group'", "'serie_facture': 'SUTRA Groupé'")
content = content.replace("'dossier_name': 'Paiement SUTRA Groupé'", "'serie_facture': 'SUTRA Groupé'")

with open(filepath_wizard, 'w', encoding='utf-8') as f:
    f.write(content)


# 2. Fix cheque.py private method
filepath_cheque = 'custom-addons/finance_2/models/cheque.py'
with open(filepath_cheque, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("def _find_matching_talon(self", "def find_matching_talon(self")
content = content.replace("self._find_matching_talon(", "self.find_matching_talon(")
content = content.replace("rec._find_matching_talon(", "rec.find_matching_talon(")

with open(filepath_cheque, 'w', encoding='utf-8') as f:
    f.write(content)


# 3. Fix server action in cheque_views.xml
filepath_views = 'custom-addons/finance_2/views/cheque_views.xml'
with open(filepath_views, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("record._find_matching_talon(", "record.find_matching_talon(")

with open(filepath_views, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixes applied successfully")
