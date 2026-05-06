from odoo import models, fields


class EffetsOwner(models.Model):
    """
    Represents a third-party person/company whose name appears on a cheque
    or effet when the payment is not in the client's own name.
    """
    _name = 'tresorerie_chq.effets.owner'
    _description = 'Porteur de Chèque / Effet'
    _order = 'name'

    name = fields.Char(string='Nom du porteur', required=True)
    phone = fields.Char(string='Téléphone')
    note = fields.Text(string='Remarques')

    # Back-reference: all cheque lines that reference this owner
    cheque_line_ids = fields.One2many(
        'tresorerie_chq.paiement.cheque.line',
        'owner_id',
        string='Chèques',
        readonly=True,
    )

    # Back-reference: all effet lines that reference this owner
    effet_line_ids = fields.One2many(
        'tresorerie_chq.paiement.effet.line',
        'owner_id',
        string='Effets',
        readonly=True,
    )
