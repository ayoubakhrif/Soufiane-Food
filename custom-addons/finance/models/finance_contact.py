from odoo import models, fields, api

class FinanceContact(models.Model):
    _name = 'finance.contact'
    _description = 'Contacts Finance'
    _order = 'name desc'

    contact_sf_id = fields.Many2one('contacts.casa', string='Contact SF', required=True)
    name = fields.Char(string='Nom')
    telephone = fields.Char(string='Téléphone')
    gmail = fields.Char(string='Gmail')
    ste = fields.Char(string='Société')
    commentaire = fields.Text(string='Commentaire')

    @api.onchange('contact_sf_id')
    def _onchange_contact_sf_id(self):
        if self.contact_sf_id:
            self.name = self.contact_sf_id.name
            self.telephone = self.contact_sf_id.telephone
            self.gmail = self.contact_sf_id.gmail
            self.ste = self.contact_sf_id.ste
            self.commentaire = self.contact_sf_id.commentaire
