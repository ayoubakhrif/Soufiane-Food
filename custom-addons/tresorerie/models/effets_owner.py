from odoo import models, fields


class EffetsOwner(models.Model):
    """
    Represents a third-party person/company whose name appears on a cheque
    or effet when the payment is not in the client's own name.
    """
    _name = 'tresorerie.effets.owner'
    _description = 'Porteur de Chèque / Effet'
    _order = 'name'

    name = fields.Char(string='Nom du porteur', required=True)
    phone = fields.Char(string='Téléphone')
    note = fields.Text(string='Remarques')

    # Back-reference: all cheque lines that reference this owner
    cheque_line_ids = fields.One2many(
        'tresorerie.paiement.cheque.line',
        'owner_id',
        string='Chèques',
        readonly=True,
    )
