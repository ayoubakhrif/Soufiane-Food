import os

filepath = 'custom-addons/finance_2/models/personne.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the finance2.benif class
old_benif = """class Finance2Benif(models.Model):
    _name = 'finance2.benif'
    _description = 'Bénéficiaire'

    name = fields.Char(string='Nom du bénéficiaire', required=True)
    active = fields.Boolean(default=True)
    cheque_ids = fields.One2many('finance2.cheque', 'benif_id', string='Chèques')"""

# Be careful with encodings and weird characters. I will use a simple regex or just string replacement assuming ASCII.
# The `cat` output showed 'B\u01f8n\u01f8ficiaire' and so on. Let's just insert the fields before the end of the file.
