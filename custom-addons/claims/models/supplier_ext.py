from odoo import models, fields

class LogistiqueSupplier(models.Model):
    _inherit = 'logistique.supplier'

    dhl_claim_ids = fields.One2many(
        'claims.dhl.delay',
        'supplier_id',
        string='DHL Delay Claims',
        readonly=True
    )

    franchise_claim_ids = fields.One2many(
        'claims.franchise.difference',
        'supplier_id',
        string='Franchise Claims',
        readonly=True
    )
