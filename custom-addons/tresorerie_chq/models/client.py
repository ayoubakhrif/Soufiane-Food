from odoo import models, fields, api
from odoo.exceptions import AccessError

class TresorerieChqClientAlias(models.Model):
    _name = 'tresorerie_chq.client.alias'
    _description = 'Alias Client'

    name = fields.Char(string='Alias', required=True)
    client_id = fields.Many2one('tresorerie_chq.client', string='Client', required=True, ondelete='cascade')

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager') and not self.env.su:
            raise AccessError("Seul un responsable de la trésorerie peut ajouter des alias clients.")
        return super().create(vals_list)

class TresorerieChqClient(models.Model):
    _name = 'tresorerie_chq.client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Client (Trésorerie Chèques & Effets)'

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager') and not self.env.su:
            raise AccessError("Seul un responsable de la trésorerie peut ajouter de nouveaux clients.")
        return super().create(vals_list)

    name = fields.Char(string='Nom', required=True)
    cin = fields.Char(string='CIN')
    phone = fields.Char(string='Téléphone')
    email = fields.Char(string='E-mail')
    address = fields.Text(string='Adresse')
    emetteur = fields.Selection([
        ('soufiane', 'Soufiane'),
        ('hamza', 'Hamza'),
    ], string="Ce chq est de la part de qui", tracking=True)
    allow_no_date = fields.Boolean(
        string="Autoriser sans échéance",
        default=False,
        help="Si coché, permet d'enregistrer des chèques ou des effets sans date d'échéance pour ce client."
    )
    
    paiement_ids = fields.One2many('tresorerie_chq.paiement', 'client_id', string='Paiements')
    alias_ids = fields.One2many('tresorerie_chq.client.alias', 'client_id', string='Alias')
    
    cheque_ids = fields.One2many('tresorerie_chq.cheque', 'client_id', string='Chèques')
    effet_ids = fields.One2many('tresorerie_chq.effet', 'client_id', string='Effets')

    def get_all_cheques(self):
        self.ensure_one()
        return self.env['tresorerie_chq.cheque'].search([('client_id', '=', self.id)], order='check_date asc, id desc')

    def get_all_effets(self):
        self.ensure_one()
        return self.env['tresorerie_chq.effet'].search([('client_id', '=', self.id)], order='check_date asc, id desc')

    def get_report_summary(self):
        self.ensure_one()
        all_chqs = self.get_all_cheques()
        all_effs = self.get_all_effets()
        total_chq = sum(all_chqs.mapped('amount'))
        total_eff = sum(all_effs.mapped('amount'))
        total_encaisse = sum(all_chqs.filtered(lambda x: x.state == 'encaisse').mapped('amount')) + sum(all_effs.filtered(lambda x: x.state == 'encaisse').mapped('amount'))
        total_impaye = sum(all_chqs.filtered(lambda x: x.state == 'impaye').mapped('amount')) + sum(all_effs.filtered(lambda x: x.state == 'impaye').mapped('amount'))
        return {
            'cheques': all_chqs,
            'effets': all_effs,
            'total_chq': total_chq,
            'total_eff': total_eff,
            'total_general': total_chq + total_eff,
            'total_encaisse': total_encaisse,
            'total_impaye': total_impaye,
            'count_chq': len(all_chqs),
            'count_eff': len(all_effs),
        }

    unpaid_count = fields.Integer(string="Impayés", compute='_compute_unpaid_count', store=True)

    @api.depends('name', 'emetteur')
    def _compute_display_name(self):
        emetteur_dict = dict(self._fields['emetteur'].selection)
        for rec in self:
            if rec.emetteur:
                label = emetteur_dict.get(rec.emetteur, rec.emetteur.capitalize())
                rec.display_name = f"{label}-{rec.name}"
            else:
                rec.display_name = rec.name

    blacklist_id = fields.One2many('tresorerie_chq.blacklist.client', 'client_id', string="Fiche Liste Noire")
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

    @api.depends('cheque_ids.state', 'effet_ids.state')
    def _compute_unpaid_count(self):
        for rec in self:
            c = len(rec.cheque_ids.filtered(lambda x: x.state == 'impaye'))
            e = len(rec.effet_ids.filtered(lambda x: x.state == 'impaye'))
            rec.unpaid_count = c + e

    def _check_and_update_blacklist(self, config=None):
        """Recalcule les statistiques et met à jour ou crée la fiche de liste noire du client."""
        self.ensure_one()
        if not config:
            config = self.env['tresorerie_chq.blacklist.config'].get_config()

        all_chqs = self.env['tresorerie_chq.cheque'].search([('client_id', '=', self.id)])
        all_effets = self.env['tresorerie_chq.effet'].search([('client_id', '=', self.id)])

        total_count = len(all_chqs) + len(all_effets)
        total_amount = sum(all_chqs.mapped('amount')) + sum(all_effets.mapped('amount'))

        unpaid_chqs = all_chqs.filtered(lambda c: c.state == 'impaye')
        unpaid_effets = all_effets.filtered(lambda e: e.state == 'impaye')

        unpaid_count = len(unpaid_chqs) + len(unpaid_effets)
        unpaid_amount = sum(unpaid_chqs.mapped('amount')) + sum(unpaid_effets.mapped('amount'))

        pct_count = (unpaid_count / total_count * 100.0) if total_count > 0 else 0.0
        pct_amount = (unpaid_amount / total_amount * 100.0) if total_amount > 0 else 0.0

        is_over = (total_count >= config.client_min_count) and (
            (config.client_pct_count > 0 and pct_count >= config.client_pct_count) or
            (config.client_pct_amount > 0 and pct_amount >= config.client_pct_amount)
        )

        bl = self.env['tresorerie_chq.blacklist.client'].search([('client_id', '=', self.id)], limit=1)

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
                    'client_id': self.id,
                    'state': 'blocked',
                    'date_blacklist': fields.Datetime.now(),
                })
                self.env['tresorerie_chq.blacklist.client'].create(vals)
            else:
                if bl.state != 'alert':
                    vals['state'] = 'blocked'
                bl.write(vals)
        else:
            if bl:
                vals['state'] = 'unblocked'
                bl.write(vals)

