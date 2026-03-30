from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PortnetVirement(models.Model):
    _name = 'portnet.virement'
    _description = 'Ordre de virement'
    _order = 'id desc'

    name = fields.Char(
        string='Ordre de virement',
        required=True,
    )

    invoice = fields.Char(
        string='Facture',
        required=True,
    )

    ste_id = fields.Many2one(
        'logistique.ste',
        string='Société',
        required=True,
    )

    article_id = fields.Many2one(
        'achat.article',
        string='Article',
    )

    supplier_id = fields.Many2one(
        'logistique.supplier',
        string='Fournisseur',
    )

    total = fields.Float(
        string='Total',
    )

    container_ids = fields.Many2many(
        'logistique.container',
        string='Conteneurs',
    )

    amount_virement = fields.Float(
        string='Montant Virement',
    )

    @api.constrains('invoice', 'ste_id')
    def _check_invoice_ste(self):
        for rec in self:
            if not rec.invoice:
                continue
            # Search for other records with the same invoice
            domain = [('invoice', '=', rec.invoice), ('id', '!=', rec.id)]
            other_virements = self.search(domain)
            for other in other_virements:
                if other.ste_id != rec.ste_id:
                    raise ValidationError(
                        "L'invoice \"%s\" est déjà utilisé par une autre société (%s)!"
                        % (rec.invoice, other.ste_id.name)
                    )
