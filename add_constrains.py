import os

filepath = 'custom-addons/tanger_med/models/sutra.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_method = """    @api.constrains('name')
    def _check_unique_name(self):
        for rec in self:
            if rec.name:
                domain = [('name', '=', rec.name), ('id', '!=', rec.id)]
                if self.search_count(domain) > 0:
                    raise exceptions.ValidationError(f"La facture SUTRA '{rec.name}' a déjà été saisie (numéro de facture en double) !")

    @api.constrains('sutra_id')
    def _check_unique_dossier(self):
        for rec in self:
            if rec.sutra_id:
                domain = [('sutra_id', '=', rec.sutra_id.id), ('id', '!=', rec.id)]
                if self.search_count(domain) > 0:
                    raise exceptions.ValidationError(f"Le dossier SUTRA '{rec.sutra_id.dum or rec.sutra_id.name}' a déjà une facture SUTRA liée. Impossible d'en lier une deuxième !")
"""

# Insert right after pdf_filename
insert_marker = "pdf_filename = fields.Char(string='Nom du fichier PDF')"
content = content.replace(insert_marker, insert_marker + "\n\n" + new_method)

# Import exceptions if not imported
if "from odoo import models, fields, api, exceptions" not in content:
    content = content.replace("from odoo import models, fields, api", "from odoo import models, fields, api, exceptions")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added constrains")
