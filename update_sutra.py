import os

filepath = 'custom-addons/tanger_med/models/sutra.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace state selection
old_state = """    state = fields.Selection([
        ('non_paye', 'Non Paye'),
        ('paye', 'Paye')
    ], string='Statut Paiement', default='non_paye', tracking=True)"""
new_state = """    state = fields.Selection([
        ('non_paye', 'Non Paye'),
        ('encours', 'En Cours'),
        ('paye', 'Paye')
    ], string='Statut Paiement', default='non_paye', tracking=True)
    
    cheque_id = fields.Many2one('finance2.cheque', string='Cheque de Paiement', tracking=True)"""

if old_state in content:
    content = content.replace(old_state, new_state)
else:
    # Just in case there are subtle differences like accents
    # Fallback replacement
    import re
    content = re.sub(
        r"state = fields\.Selection\(\[.*?\]\, string='Statut Paiement', default='non_paye', tracking=True\)",
        new_state,
        content,
        flags=re.DOTALL
    )

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sutra.py")
