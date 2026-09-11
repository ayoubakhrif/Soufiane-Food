import os

filepath = 'custom-addons/finance_2/models/cheque.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add field and method
new_code = """    week = fields.Char(string="Semaine", compute="_compute_week", store=True)
    history_journals = fields.Text(string='Historique des reports', readonly=True, tracking=True)
    
    def action_reporter_cheque(self):
        for rec in self:
            if rec.week and rec.journal:
                entry = f"{rec.week} - J{rec.journal}"
                if rec.history_journals:
                    rec.history_journals += f" | {entry}"
                else:
                    rec.history_journals = entry
            rec.date_emission = False
            rec.journal = False
            rec.date_encaissement = False
            rec.talon_id = False"""

content = content.replace('    week = fields.Char(string="Semaine", compute="_compute_week", store=True)', new_code)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated cheque.py")
