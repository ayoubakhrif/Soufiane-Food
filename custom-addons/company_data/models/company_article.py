from odoo import models, fields

class CompanyArticle(models.Model):
    _name = 'company.article'
    _description = 'Article (Données Société)'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Nom interne',
        required=True
    )

    display_name = fields.Char(
        string='Nom à afficher',
        required=True
    )

    image = fields.Image(
        string='Image',
        max_width=1024,
        max_height=1024
    )

    category_id = fields.Many2one(
        'company.article.category',
        string='Catégorie',
        required=True
    )
