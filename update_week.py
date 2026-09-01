import os

base_path = r'c:\odoo-repos\Soufiane-Food\custom-addons\finance_2'
cheque_py = os.path.join(base_path, 'models', 'cheque.py')
with open(cheque_py, 'r', encoding='utf-8') as f:
    content = f.read()

if 'week = fields.Char' not in content:
    content = content.replace(
        "date_echeance = fields.Date(string=\"Date d'échéance\", tracking=True)",
        "date_echeance = fields.Date(string=\"Date d'échéance\", tracking=True)\n    week = fields.Char(string=\"Semaine\", compute=\"_compute_week\", store=True)"
    )
    
    compute_week = """
    @api.depends('date_emission')
    def _compute_week(self):
        for rec in self:
            if rec.date_emission:
                import datetime
                # Use standard isocalendar to match week number
                isocal = rec.date_emission.isocalendar()
                week_num = isocal[1]
                rec.week = f"W{week_num:02d}"
            else:
                rec.week = False
"""
    content = content.replace('def _compute_is_admin(self):', compute_week + '\n    def _compute_is_admin(self):')
    with open(cheque_py, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Week field added to cheque.py')
