import re

filepath = 'c:/odoo-repos/Soufiane-Food/custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update action_confirmer (Remove amount_total and date_echeance)
old_confirmer = """    def action_confirmer(self):
        for rec in self:
            missing_fields = []
            if not rec.journal:
                missing_fields.append("Journal")
            if not rec.name:
                missing_fields.append("N° Chèque")
            if not rec.amount_total:
                missing_fields.append("Montant Total")
            if not rec.date_emission:
                missing_fields.append("Date d'émission")
            if not rec.date_echeance:
                missing_fields.append("Date d'échéance")
            if not rec.ste_id:
                missing_fields.append("Société")
                
            if missing_fields:
                raise UserError("Vous ne pouvez pas confirmer ce chèque car les informations suivantes sont manquantes : " + ", ".join(missing_fields))
                
            rec.state = 'reserve'"""

new_confirmer = """    def action_confirmer(self):
        for rec in self:
            missing_fields = []
            if not rec.journal:
                missing_fields.append("Journal")
            if not rec.name:
                missing_fields.append("N° Chèque")
            if not rec.date_emission:
                missing_fields.append("Date d'émission")
            if not rec.ste_id:
                missing_fields.append("Société")
                
            if missing_fields:
                raise UserError("Vous ne pouvez pas confirmer ce chèque car les informations suivantes sont manquantes : " + ", ".join(missing_fields))
                
            rec.state = 'reserve'"""

content = content.replace(old_confirmer, new_confirmer)

# 2. Update action_cloturer (Add amount_total and date_echeance)
old_cloturer = """    def action_cloturer(self):
        for rec in self:
            rec.state = 'cloture'"""

new_cloturer = """    def action_cloturer(self):
        for rec in self:
            missing_fields = []
            if not rec.amount_total:
                missing_fields.append("Montant Total")
            if not rec.date_echeance:
                missing_fields.append("Date d'échéance")
                
            if missing_fields:
                raise UserError("Vous ne pouvez pas clôturer ce chèque car les informations suivantes sont manquantes : " + ", ".join(missing_fields))
                
            rec.state = 'cloture'"""

content = content.replace(old_cloturer, new_cloturer)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated cheque.py validations.")
