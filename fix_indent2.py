import os
import re

filepath = 'custom-addons/finance/models/finance_benif.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the indentation of total_chqs
content = content.replace("                total_chqs = len(chqs) + len(effets)", "        total_chqs = len(chqs) + len(effets)")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed indentation")
