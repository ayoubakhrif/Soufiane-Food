from odoo import models, fields

class LogistiqueContainer(models.Model):
    _name = 'logistique.container'
    _description = 'Conteneur'

    name = fields.Char(string='Numéro Conteneur', required=True)
    dossier_id = fields.Many2one('logistique.dossier', string='Dossier / BL')
