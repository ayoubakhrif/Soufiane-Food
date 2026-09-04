from odoo import models, fields, api


class EffetsOwner(models.Model):
    """
    Represents a third-party person/company whose name appears on a cheque
    or effet when the payment is not in the client's own name.
    """
    _name = 'tresorerie_chq.effets.owner'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Porteur de Chèques / Effets'
    _order = 'name'

    name = fields.Char(string='Nom du porteur', required=True)
    cin = fields.Char(string='CIN')
    phone = fields.Char(string='Téléphone')
    note = fields.Text(string='Remarques')

    # Back-reference: all cheque lines that reference this owner
    cheque_line_ids = fields.One2many(
        'tresorerie_chq.cheque',
        'owner_id',
        string='Chèques',
        readonly=True,
    )

    # Back-reference: all effet lines that reference this owner
    effet_line_ids = fields.One2many(
        'tresorerie_chq.effet',
        'owner_id',
        string='Effets',
        readonly=True,
    )

    cheque_count = fields.Integer(string="Nombre de chèques", compute='_compute_counts', store=True)
    effet_count = fields.Integer(string="Nombre d'effets", compute='_compute_counts', store=True)
    unpaid_count = fields.Integer(string="Impayés", compute='_compute_counts', store=True)

    @api.depends('cheque_line_ids.state', 'effet_line_ids.state')
    def _compute_counts(self):
        for rec in self:
            rec.cheque_count = len(rec.cheque_line_ids)
            rec.effet_count = len(rec.effet_line_ids)
            rec.unpaid_count = len(rec.cheque_line_ids.filtered(lambda x: x.state == 'impaye')) + \
                               len(rec.effet_line_ids.filtered(lambda x: x.state == 'impaye'))
