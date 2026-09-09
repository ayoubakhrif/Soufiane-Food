import os

filepath = 'custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Add the field and compute method
for i, line in enumerate(lines):
    if "montant_encaisse = fields.Float(" in line:
        insert_idx = i + 1
        new_lines = [
            "    difference = fields.Float(string=\"Différence\", compute=\"_compute_difference\", store=True)\n",
            "\n",
            "    @api.depends('amount_total', 'montant_encaisse')\n",
            "    def _compute_difference(self):\n",
            "        for rec in self:\n",
            "            if rec.state == 'encaisse' or rec.montant_encaisse:\n",
            "                rec.difference = rec.amount_total - rec.montant_encaisse\n",
            "            else:\n",
            "                rec.difference = 0.0\n"
        ]
        lines = lines[:insert_idx] + new_lines + lines[insert_idx:]
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
