from odoo import models, fields

class TvaDesignation(models.Model):
    _name = 'tva.designation'
    _description = 'Désignation TVA'

    name = fields.Char(string='Nom de désignation', required=True)
    tva_rate = fields.Float(string='Taux de TVA (%)')
    tva_code = fields.Char(string='Code TVA')
    type_designation = fields.Selection([
        ('achats_non_immob', 'Achats non immobilisés'),
        ('immob', 'Immobilisations'),
        ('autres_achats_non_immob', 'Autres achats non immobilisés')
    ], string='Type de désignation', required=True)
