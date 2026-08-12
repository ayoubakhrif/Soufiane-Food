import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The incorrect code at the end
incorrect_code = """
    def force_brouillon(self):
        for rec in self:
            rec.state = 'brouillon'

    def force_reserve(self):
        for rec in self:
            rec.state = 'reserve'

    def force_actif(self):
        for rec in self:
            rec.state = 'actif'

    def force_cloture(self):
        for rec in self:
            rec.state = 'cloture'
"""

# Remove from end
if content.endswith(incorrect_code):
    content = content[:-len(incorrect_code)]
else:
    # Try replacing if it's not at the very end
    content = content.replace(incorrect_code, "")

# Insert before Finance2Repartition
target = "class Finance2Repartition(models.Model):"
content = content.replace(target, incorrect_code + "\n" + target)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed location of force methods in cheque.py")
