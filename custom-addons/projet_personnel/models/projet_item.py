from odoo import models, fields, api

class ProjetItem(models.Model):
    _name = 'projet.item'
    _description = 'Catalogue Article'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom de l\'article', required=True, tracking=True)
    image = fields.Image(string='Image (Défaut)', max_width=1024, max_height=1024)
    color_ids = fields.One2many('projet.item.color', 'item_id', string='Couleurs')

class ProjetItemColor(models.Model):
    _name = 'projet.item.color'
    _description = 'Couleur d\'Article'

    item_id = fields.Many2one('projet.item', string='Article', required=True, ondelete='cascade')
    name = fields.Char(string='Couleur', required=True)
    image = fields.Image(string='Image de la couleur', max_width=1024, max_height=1024)
