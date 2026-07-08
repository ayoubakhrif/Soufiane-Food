from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SuiviProduit(models.Model):
    _name = 'suivi.produit'
    _description = 'Produit Suivi Transport'
    _order = 'id desc'

    name = fields.Char(string='Nom', required=True)
    article_id = fields.Many2one('company.article', string='Article (Company)', required=True)
    image_1920 = fields.Image(related='article_id.image', string='Image', store=True, readonly=True)

    @api.constrains('article_id')
    def _check_article_id_unique(self):
        for record in self:
            if record.article_id:
                domain = [('id', '!=', record.id), ('article_id', '=', record.article_id.id)]
                if self.search_count(domain) > 0:
                    raise ValidationError("Cet article est déjà utilisé pour un autre produit ! Vous ne pouvez pas le choisir deux fois.")
    @api.constrains('name')
    def _check_name_unique(self):
        for record in self:
            if not record.name:
                continue
            domain = [('id', '!=', record.id), ('name', '=ilike', record.name)]
            if self.search_count(domain) > 0:
                raise ValidationError(f"Le produit '{record.name}' existe déjà.")
