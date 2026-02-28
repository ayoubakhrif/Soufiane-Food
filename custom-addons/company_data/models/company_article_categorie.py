from odoo import models, fields

class CompanyArticleCategory(models.Model):
    _name = 'company.article.category'
    _description = 'Catégorie Article (Société)'
    _rec_name = 'name'

    name = fields.Char(
        string='Catégorie',
        required=True
    )

    vat_rate = fields.Float(
        string='TVA (%)',
        required=True,
        help='Exemple : 20 pour 20%'
    )
