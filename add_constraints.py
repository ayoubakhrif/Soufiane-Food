import os

filepath = 'custom-addons/tanger_med/models/sutra.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure ValidationError is imported
if 'from odoo.exceptions import ValidationError' not in content and 'from odoo.exceptions import UserError, ValidationError' not in content:
    if 'from odoo.exceptions import UserError' in content:
        content = content.replace('from odoo.exceptions import UserError', 'from odoo.exceptions import UserError, ValidationError')
    else:
        content = content.replace('from odoo import models, fields, api', 'from odoo import models, fields, api\nfrom odoo.exceptions import ValidationError')

new_constraints = """    pdf_filename = fields.Char(string='Nom du fichier PDF')

    @api.constrains('name')
    def _check_unique_name(self):
        for rec in self:
            if rec.name:
                duplicates = self.search([('name', '=', rec.name), ('id', '!=', rec.id)])
                if duplicates:
                    raise ValidationError(f"La facture SUTRA '{rec.name}' a déjà été saisie dans le système !")

    @api.constrains('sutra_id', 'amount')
    def _check_unique_dossier_amount(self):
        for rec in self:
            if rec.sutra_id and rec.amount:
                duplicates = self.search([
                    ('sutra_id', '=', rec.sutra_id.id),
                    ('amount', '=', rec.amount),
                    ('id', '!=', rec.id)
                ])
                if duplicates:
                    raise ValidationError(f"Une facture avec le même montant ({rec.amount} DH) existe déjà pour le dossier {rec.sutra_id.name} (DUM: {rec.sutra_id.dum or 'N/A'}) !")
"""

content = content.replace("    pdf_filename = fields.Char(string='Nom du fichier PDF')", new_constraints)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added constraints to sutra.py")
