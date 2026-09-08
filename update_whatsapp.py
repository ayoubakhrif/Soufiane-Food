import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

import re
old_reste = r"sum\(c\.amount_total for c in benif\.physical_chq_ids if not c\.date_encaissement\) \+ sum\(e\.montant for e in benif\.effet_ids if not e\.date_encaissement\)"
new_reste = "sum(c.amount_total for c in benif.physical_chq_ids if not c.date_encaissement) + sum(e.montant for e in benif.effet_ids if not e.date_encaissement) + sum(f.amount_total for f in benif.get_finance2_cheques(True))"

content = re.sub(old_reste, new_reste, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated whatsapp_finance_api.py")
