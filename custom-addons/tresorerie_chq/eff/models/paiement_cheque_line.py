from odoo import models, fields, api


class PaiementChequeLine(models.Model):
    """
    One line = one physical cheque received within a paiement.
    """
    _name = 'tresorerie_chq.paiement.cheque.line'
    _description = 'Ligne de Chèque'
    _order = 'check_date, id'

    paiement_id = fields.Many2one(
        'tresorerie_chq.paiement',
        string='Paiement',
        required=True,
        ondelete='cascade',
    )

    owner_id = fields.Many2one(
        'tresorerie_chq.effets.owner',
        string='Porteur',
        ondelete='restrict',
        help="Laisser vide si le chèque est au nom du client. "
             "Sélectionner le porteur si le chèque est un effet de commerce.",
    )

    # Specific field for "Soufiane" client
    soufiane_owner_id = fields.Many2one(
        'tresorerie_chq.effets.owner',
        string='Client soufiane',
        ondelete='restrict',
    )

    check_date = fields.Date(
        string="Date d'échéance",
        required=True,
    )
    amount = fields.Float(
        string='Montant',
        required=True,
        digits=(10, 2),
    )
    note = fields.Char(string='N° chèque')

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


class PaiementEffetLine(models.Model):
    """
    One line = one physical effet received within a paiement.
    """
    _name = 'tresorerie_chq.paiement.effet.line'
    _description = 'Ligne d\'Effet'
    _order = 'check_date, id'

    paiement_id = fields.Many2one(
        'tresorerie_chq.paiement',
        string='Paiement',
        required=True,
        ondelete='cascade',
    )

    owner_id = fields.Many2one(
        'tresorerie_chq.effets.owner',
        string='Porteur',
        ondelete='restrict',
        help="Laisser vide si l'effet est au nom du client. "
             "Sélectionner le porteur si l'effet est un effet de commerce.",
    )

    # Specific field for "Soufiane" client
    soufiane_owner_id = fields.Many2one(
        'tresorerie_chq.effets.owner',
        string='Client soufiane',
        ondelete='restrict',
    )

    check_date = fields.Date(
        string="Date d'échéance",
        required=True,
    )
    amount = fields.Float(
        string='Montant',
        required=True,
        digits=(10, 2),
    )
    note = fields.Char(string='N° effet')

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
