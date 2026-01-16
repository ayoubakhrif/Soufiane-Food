from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re

class LogistiqueSupplier(models.Model):
    _name = 'logistique.supplier'
    _description = 'Fournisseur'

    name = fields.Char(string='Nom', required=True)
    email = fields.Char(string='Email')



    @api.constrains('email')
    def _check_email_format(self):
        email_regex = r'^[^@]+@[^@]+\.[^@]+$'
        for rec in self:
            if rec.email and not re.match(email_regex, rec.email):
                raise ValidationError("Invalid email format.")
