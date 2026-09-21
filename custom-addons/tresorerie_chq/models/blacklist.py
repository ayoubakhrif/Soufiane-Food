# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError

class TresorerieChqBlacklistConfig(models.Model):
    _name = 'tresorerie_chq.blacklist.config'
    _description = 'Configuration Paramètres Liste Noire'

    name = fields.Char(string="Nom", default="Paramètres Liste Noire", readonly=True)

    # Paramètres Client
    client_min_count = fields.Integer(
        string="Clients : Min. Chèques/Effets", 
        default=2, 
        help="Nombre minimum de chèques/effets traités requis pour activer le contrôle de liste noire."
    )
    client_pct_count = fields.Float(
        string="Clients : Seuil en Nombre (%)", 
        default=15.0, 
        help="Pourcentage maximum d'impayés en nombre autorisé avant mise en liste noire."
    )
    client_pct_amount = fields.Float(
        string="Clients : Seuil en Montant (%)", 
        default=20.0, 
        help="Pourcentage maximum d'impayés en montant autorisé avant mise en liste noire."
    )

    # Paramètres Porteur
    owner_min_count = fields.Integer(
        string="Porteurs : Min. Chèques/Effets", 
        default=2, 
        help="Nombre minimum de chèques/effets traités requis pour activer le contrôle de liste noire."
    )
    owner_pct_count = fields.Float(
        string="Porteurs : Seuil en Nombre (%)", 
        default=10.0, 
        help="Pourcentage maximum d'impayés en nombre autorisé avant mise en liste noire."
    )
    owner_pct_amount = fields.Float(
        string="Porteurs : Seuil en Montant (%)", 
        default=15.0, 
        help="Pourcentage maximum d'impayés en montant autorisé avant mise en liste noire."
    )

    @api.model
    def get_config(self):
        config = self.search([], limit=1)
        if not config:
            config = self.create({})
        return config

    def action_recompute_all(self):
        """Recalcule instantanément le statut de liste noire pour tous les clients et porteurs."""
        if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
            raise AccessError("Seul un responsable peut lancer le recalcul global.")
            
        clients = self.env['tresorerie_chq.client'].search([])
        for client in clients:
            client._check_and_update_blacklist(config=self)

        owners = self.env['tresorerie_chq.effets.owner'].search([])
        for owner in owners:
            owner._check_and_update_blacklist(config=self)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Recalcul terminé',
                'message': f"Les listes noires ont été mises à jour pour {len(clients)} clients et {len(owners)} porteurs.",
                'type': 'success',
                'sticky': False,
            }
        }


class TresorerieChqBlacklistClient(models.Model):
    _name = 'tresorerie_chq.blacklist.client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Liste Noire Client'
    _order = 'state asc, pct_amount desc, id desc'

    client_id = fields.Many2one(
        'tresorerie_chq.client', 
        string="Client", 
        required=True, 
        ondelete='cascade', 
        tracking=True
    )
    name = fields.Char(related='client_id.name', string="Nom du Client", store=True, readonly=True)
    cin = fields.Char(related='client_id.cin', string="CIN", readonly=True)
    phone = fields.Char(related='client_id.phone', string="Téléphone", readonly=True)

    total_count = fields.Integer(string="Total Chèques/Effets", readonly=True)
    unpaid_count = fields.Integer(string="Total Impayés", readonly=True, tracking=True)
    pct_count = fields.Float(string="Taux Impayés (Nombre %)", readonly=True, digits=(5, 2))

    total_amount = fields.Float(string="Montant Total Traité (MAD)", readonly=True, digits=(10, 2))
    unpaid_amount = fields.Float(string="Montant Total Impayé (MAD)", readonly=True, digits=(10, 2), tracking=True)
    pct_amount = fields.Float(string="Taux Impayés (Montant %)", readonly=True, digits=(5, 2))

    state = fields.Selection([
        ('blocked', '🔴 Blacklisté'),
        ('alert', '🟡 Débloqué avec alerte'),
        ('unblocked', '🟢 Débloqué'),
    ], string="Statut", default='blocked', required=True, tracking=True)

    reason = fields.Text(string="Motif / Remarques du responsable", tracking=True)
    date_blacklist = fields.Datetime(string="Date d'inscription", default=fields.Datetime.now, readonly=True)
    date_update = fields.Datetime(string="Dernière mise à jour", default=fields.Datetime.now, readonly=True)

    _sql_constraints = [
        ('client_unique', 'unique(client_id)', "Ce client est déjà enregistré dans la liste noire.")
    ]

    def action_set_alert(self):
        """Passer en 'Débloqué avec alerte' (réservé au responsable)."""
        if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
            raise AccessError("Seul un responsable peut débloquer avec alerte.")
        for rec in self:
            rec.write({
                'state': 'alert',
                'date_update': fields.Datetime.now()
            })
            rec.message_post(body="🟡 Client débloqué avec alerte par le responsable.")

    def action_set_blocked(self):
        """Rebloquer le client."""
        if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
            raise AccessError("Seul un responsable peut modifier le statut de liste noire.")
        for rec in self:
            rec.write({
                'state': 'blocked',
                'date_update': fields.Datetime.now()
            })
            rec.message_post(body="🔴 Client rebloqué sur liste noire par le responsable.")

    def action_set_unblocked(self):
        """Débloquer manuellement."""
        if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
            raise AccessError("Seul un responsable peut débloquer manuellement.")
        for rec in self:
            rec.write({
                'state': 'unblocked',
                'date_update': fields.Datetime.now()
            })
            rec.message_post(body="🟢 Client débloqué manuellement par le responsable.")


class TresorerieChqBlacklistOwner(models.Model):
    _name = 'tresorerie_chq.blacklist.owner'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Liste Noire Porteur'
    _order = 'state asc, pct_amount desc, id desc'

    owner_id = fields.Many2one(
        'tresorerie_chq.effets.owner', 
        string="Porteur", 
        required=True, 
        ondelete='cascade', 
        tracking=True
    )
    name = fields.Char(related='owner_id.name', string="Nom du Porteur", store=True, readonly=True)
    cin = fields.Char(related='owner_id.cin', string="CIN", readonly=True)
    phone = fields.Char(related='owner_id.phone', string="Téléphone", readonly=True)

    total_count = fields.Integer(string="Total Chèques/Effets", readonly=True)
    unpaid_count = fields.Integer(string="Total Impayés", readonly=True, tracking=True)
    pct_count = fields.Float(string="Taux Impayés (Nombre %)", readonly=True, digits=(5, 2))

    total_amount = fields.Float(string="Montant Total Traité (MAD)", readonly=True, digits=(10, 2))
    unpaid_amount = fields.Float(string="Montant Total Impayé (MAD)", readonly=True, digits=(10, 2), tracking=True)
    pct_amount = fields.Float(string="Taux Impayés (Montant %)", readonly=True, digits=(5, 2))

    state = fields.Selection([
        ('blocked', '🔴 Blacklisté'),
        ('alert', '🟡 Débloqué avec alerte'),
        ('unblocked', '🟢 Débloqué'),
    ], string="Statut", default='blocked', required=True, tracking=True)

    reason = fields.Text(string="Motif / Remarques du responsable", tracking=True)
    date_blacklist = fields.Datetime(string="Date d'inscription", default=fields.Datetime.now, readonly=True)
    date_update = fields.Datetime(string="Dernière mise à jour", default=fields.Datetime.now, readonly=True)

    _sql_constraints = [
        ('owner_unique', 'unique(owner_id)', "Ce porteur est déjà enregistré dans la liste noire.")
    ]

    def action_set_alert(self):
        """Passer en 'Débloqué avec alerte' (réservé au responsable)."""
        if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
            raise AccessError("Seul un responsable peut débloquer avec alerte.")
        for rec in self:
            rec.write({
                'state': 'alert',
                'date_update': fields.Datetime.now()
            })
            rec.message_post(body="🟡 Porteur débloqué avec alerte par le responsable.")

    def action_set_blocked(self):
        """Rebloquer le porteur."""
        if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
            raise AccessError("Seul un responsable peut modifier le statut de liste noire.")
        for rec in self:
            rec.write({
                'state': 'blocked',
                'date_update': fields.Datetime.now()
            })
            rec.message_post(body="🔴 Porteur rebloqué sur liste noire par le responsable.")

    def action_set_unblocked(self):
        """Débloquer manuellement."""
        if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
            raise AccessError("Seul un responsable peut débloquer manuellement.")
        for rec in self:
            rec.write({
                'state': 'unblocked',
                'date_update': fields.Datetime.now()
            })
            rec.message_post(body="🟢 Porteur débloqué manuellement par le responsable.")
