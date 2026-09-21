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

    blacklist_id = fields.One2many('tresorerie_chq.blacklist.owner', 'owner_id', string="Fiche Liste Noire")
    blacklist_state = fields.Selection(
        [
            ('blocked', '🔴 Blacklisté'),
            ('alert', '🟡 Débloqué avec alerte'),
            ('unblocked', '🟢 Débloqué'),
        ],
        string="Statut Liste Noire",
        compute='_compute_blacklist_state',
        store=True,
    )
    is_blacklisted = fields.Boolean(
        string="Est Blacklisté",
        compute='_compute_blacklist_state',
        store=True,
    )

    @api.depends('blacklist_id.state')
    def _compute_blacklist_state(self):
        for rec in self:
            bl = rec.blacklist_id[:1]
            rec.blacklist_state = bl.state if bl else False
            rec.is_blacklisted = (bl.state == 'blocked') if bl else False

    @api.depends('cheque_line_ids.state', 'effet_line_ids.state')
    def _compute_counts(self):
        for rec in self:
            rec.cheque_count = len(rec.cheque_line_ids)
            rec.effet_count = len(rec.effet_line_ids)
            rec.unpaid_count = len(rec.cheque_line_ids.filtered(lambda x: x.state == 'impaye')) + \
                               len(rec.effet_line_ids.filtered(lambda x: x.state == 'impaye'))

    def _check_and_update_blacklist(self, config=None):
        """Recalcule les statistiques et met à jour ou crée la fiche de liste noire du porteur."""
        self.ensure_one()
        if not config:
            config = self.env['tresorerie_chq.blacklist.config'].get_config()

        all_chqs = self.env['tresorerie_chq.cheque'].search([('owner_id', '=', self.id)])
        all_effets = self.env['tresorerie_chq.effet'].search([('owner_id', '=', self.id)])

        total_count = len(all_chqs) + len(all_effets)
        total_amount = sum(all_chqs.mapped('amount')) + sum(all_effets.mapped('amount'))

        unpaid_chqs = all_chqs.filtered(lambda c: c.state == 'impaye')
        unpaid_effets = all_effets.filtered(lambda e: e.state == 'impaye')

        unpaid_count = len(unpaid_chqs) + len(unpaid_effets)
        unpaid_amount = sum(unpaid_chqs.mapped('amount')) + sum(unpaid_effets.mapped('amount'))

        pct_count = (unpaid_count / total_count * 100.0) if total_count > 0 else 0.0
        pct_amount = (unpaid_amount / total_amount * 100.0) if total_amount > 0 else 0.0

        is_over = (total_count >= config.owner_min_count) and (
            (config.owner_pct_count > 0 and pct_count >= config.owner_pct_count) or
            (config.owner_pct_amount > 0 and pct_amount >= config.owner_pct_amount)
        )

        bl = self.env['tresorerie_chq.blacklist.owner'].search([('owner_id', '=', self.id)], limit=1)

        vals = {
            'total_count': total_count,
            'unpaid_count': unpaid_count,
            'pct_count': round(pct_count, 2),
            'total_amount': round(total_amount, 2),
            'unpaid_amount': round(unpaid_amount, 2),
            'pct_amount': round(pct_amount, 2),
            'date_update': fields.Datetime.now(),
        }

        if is_over:
            if not bl:
                vals.update({
                    'owner_id': self.id,
                    'state': 'blocked',
                    'date_blacklist': fields.Datetime.now(),
                })
                self.env['tresorerie_chq.blacklist.owner'].create(vals)
            else:
                if bl.state != 'alert':
                    vals['state'] = 'blocked'
                bl.write(vals)
        else:
            if bl:
                vals['state'] = 'unblocked'
                bl.write(vals)

