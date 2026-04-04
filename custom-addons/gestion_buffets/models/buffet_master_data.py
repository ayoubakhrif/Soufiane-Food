from odoo import models, fields

class BuffetPack(models.Model):
    _name = 'buffet.pack'
    _description = 'Pack Buffet'

    name = fields.Char(string='Nom du Pack', required=True)
    price_person = fields.Float(string='Prix par Personne', required=True)

class BuffetPlace(models.Model):
    _name = 'buffet.place'
    _description = 'Lieu du Buffet'

    name = fields.Char(string='Lieu de l\'événement', required=True)
