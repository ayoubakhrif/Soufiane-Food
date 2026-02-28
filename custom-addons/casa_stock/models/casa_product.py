from odoo import models, fields, api

class CasaProduct(models.Model):
    _name = 'casa.product'
    _description = 'Produits Casa'
    _order = 'id desc'

    name = fields.Char(string='Nom', required=True)
    article_id = fields.Many2one('company.article', string='Article (Company)', required=True)
    image_1920 = fields.Image(related='article_id.image', string='Image', store=True, readonly=True)

    _sql_constraints = [
        ('article_id_uniq', 'unique(article_id)', 'Ce produit est déjà rentré dans le système !'),
    ]

    @api.constrains('article_id')
    def _check_article_id_unique(self):
        for record in self:
            if self.search([('article_id', '=', record.article_id.id), ('id', '!=', record.id)]):
                raise models.ValidationError('Ce produit est déjà rentré dans le système !')
