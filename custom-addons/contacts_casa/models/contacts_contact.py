from odoo import models, fields


class ContactsCasa(models.Model):
    _name = 'contacts.casa'
    _description = 'Contacts Casa'
    _rec_name = 'name'

    name = fields.Char(string='Nom', required=True)
    telephone = fields.Char(string='Téléphone')
    gmail = fields.Char(string='Gmail')
    ste = fields.Char(string='Société')
    commentaire = fields.Text(string='Commentaire')
