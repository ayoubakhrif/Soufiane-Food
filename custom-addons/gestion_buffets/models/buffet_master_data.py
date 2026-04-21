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

class BuffetComposant(models.Model):
    _name = 'buffet.composant'
    _description = 'Composant'

    name = fields.Char(string='Nom', required=True)
    price = fields.Float(string='Prix', required=True, default=0.0)
    image = fields.Image(string='Image', max_width=128, max_height=128)
