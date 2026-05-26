import os

filepath = r"c:\odoo-repos\Soufiane-Food\custom-addons\tresorerie_chq\models\paiement.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

old_code = '''    @api.onchange('reception_date')
    def _onchange_reception_date(self):
        if self.reception_date:
            for line in self.cheque_line_ids:
                if not line.reception_date:
                    line.reception_date = self.reception_date
            for line in self.effet_line_ids:
                if not line.reception_date:
                    line.reception_date = self.reception_date'''

new_code = '''    @api.onchange('reception_date')
    def _onchange_reception_date(self):
        if self.reception_date:
            for line in self.cheque_line_ids:
                line.reception_date = self.reception_date
            for line in self.effet_line_ids:
                line.reception_date = self.reception_date'''

content = content.replace(old_code, new_code)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
