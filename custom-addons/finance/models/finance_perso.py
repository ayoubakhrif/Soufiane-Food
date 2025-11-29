from odoo import models, fields

class FinancePerso(models.Model):
    _name = 'finance.perso'
    _description = 'Personnes'

    name = fields.Char(string='Personnes', required=True)

    def _get_annule_perso(self):
        return self.env['finance.perso'].search([('name', '=', 'Annulé')], limit=1)
