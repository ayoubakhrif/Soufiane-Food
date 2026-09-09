import os

filepath = 'custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

method = """
    def action_encaisser(self):
        for rec in self:
            if rec.state != 'cloture':
                raise UserError("Seuls les chèques clôturés peuvent être encaissés.")
            if not rec.date_encaissement:
                raise UserError("Veuillez renseigner la date d'encaissement.")
            if not rec.montant_encaisse:
                raise UserError("Veuillez renseigner le montant encaissé.")
                
            rec.state = 'encaisse'

    def action_annuler_encaissement(self):
        for rec in self:
            if rec.state == 'encaisse':
                rec.state = 'cloture'
                rec.date_encaissement = False
                rec.montant_encaisse = 0.0
"""
if "def action_annuler_encaissement" not in content:
    # We replace action_encaisser entirely to insert our new method below it
    old_method = """    def action_encaisser(self):
        for rec in self:
            if rec.state != 'cloture':
                raise UserError("Seuls les chèques clôturés peuvent être encaissés.")
            if not rec.date_encaissement:
                raise UserError("Veuillez renseigner la date d'encaissement.")
            if not rec.montant_encaisse:
                raise UserError("Veuillez renseigner le montant encaissé.")
                
            rec.state = 'encaisse'"""
    content = content.replace(old_method, method.strip())
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
print("Updated python model")
