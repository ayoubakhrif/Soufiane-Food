import os

filepath = 'custom-addons/tanger_med/models/sutra.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace fields in config
content = content.replace("amount = fields.Float(string='Montant par defaut', required=True)", 
                          "amount_single = fields.Float(string='Montant (1 Conteneur)', required=True)\n    amount_multiple = fields.Float(string='Montant (Plusieurs)', required=True)")

# Replace create method logic
old_create = """                        config = self.env['sutra.config.ste'].search([('ste_id', '=', log_entry.ste_id.id)], limit=1)
                        if config:
                            vals['amount'] = config.amount"""
new_create = """                        config = self.env['sutra.config.ste'].search([('ste_id', '=', log_entry.ste_id.id)], limit=1)
                        if config:
                            if log_entry.container_count and log_entry.container_count > 1:
                                vals['amount'] = config.amount_multiple
                            else:
                                vals['amount'] = config.amount_single"""
content = content.replace(old_create, new_create)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated python model")
