import os
import re

filepath = 'custom-addons/finance/models/finance_benif.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the indentation
content = content.replace("        def _compute_chq_totals(self):\n        for rec in self:", "    def _compute_chq_totals(self):\n        for rec in self:")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed indentation")
