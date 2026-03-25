from odoo import models, fields, api


class PaiementChequeLine(models.Model):
    """
    One line = one physical cheque / effet received within a paiement.
    The paiement amount is computed as the sum of all its lines.
    """
    _name = 'tresorerie.paiement.cheque.line'
    _description = 'Ligne de Chèque / Effet'
    _order = 'check_date, id'

    paiement_id = fields.Many2one(
        'tresorerie.paiement',
        string='Paiement',
        required=True,
        ondelete='cascade',
    )

    # Who signed the cheque.
    # Empty (False) = the client himself.
    # Otherwise = a third-party from effets_owner.
    owner_id = fields.Many2one(
        'tresorerie.effets.owner',
        string='Porteur',
        ondelete='restrict',
        help="Laisser vide si le chèque est au nom du client. "
             "Sélectionner le porteur si le chèque est un effet de commerce.",
    )

    check_date = fields.Date(
        string="Date d'échéance",
        required=True,
    )
    amount = fields.Float(
        string='Montant (MAD)',
        required=True,
        digits=(10, 2),
    )
    note = fields.Char(string='N° chèque')

    # Convenience display: shows owner name or client name
    owner_display = fields.Char(
        string='Porteur',
        compute='_compute_owner_display',
        store=False,
    )

    @api.depends('owner_id', 'paiement_id.client_id')
    def _compute_owner_display(self):
        for line in self:
            if line.owner_id:
                line.owner_display = line.owner_id.name
            elif line.paiement_id.client_id:
                line.owner_display = line.paiement_id.client_id.name
            else:
                line.owner_display = ''
