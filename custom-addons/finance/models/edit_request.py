from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta

class FinanceEditRequest(models.Model):
    _name = 'finance.edit.request'
    _description = 'Demande d\'autorisation de modification'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'cheque_id'
    _order = 'create_date desc'

    cheque_id = fields.Many2one('datacheque', string='Chèque', required=True, ondelete='cascade', tracking=True)
    requested_by = fields.Many2one('res.users', string='Demandé par', default=lambda self: self.env.user, readonly=True, tracking=True)
    reason = fields.Text(string='Raison de la modification', required=True, tracking=True)
    state = fields.Selection([
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ], string='État', default='pending', required=True, tracking=True)
    approved_by = fields.Many2one('res.users', string='Approuvé par', readonly=True, tracking=True)
    response_date = fields.Datetime(string='Date de réponse', readonly=True, tracking=True)
    response_note = fields.Text(string='Note de réponse', tracking=True)

    def action_approve(self):
        """Approve edit request and unlock cheque for 2 days."""
        self.ensure_one()
        if not self.env.user.has_group('finance.group_finance_user'):
            raise UserError("Seuls les managers peuvent approuver les demandes de modification.")
        
        unlock_until = fields.Datetime.now() + timedelta(days=2)
        self.cheque_id.sudo().write({'unlock_until': unlock_until})
        
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'response_date': fields.Datetime.now(),
        })
        
        # Send notification to requester
        self.message_post(
            body=f"Demande approuvée par {self.env.user.name}. Le chèque peut être modifié jusqu'au {unlock_until.strftime('%Y-%m-%d %H:%M')}.",
            subject="Demande de modification approuvée",
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Demande approuvée',
                'message': 'Le chèque peut être modifié pendant 2 jours.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reject(self):
        """Reject edit request."""
        self.ensure_one()
        if not self.env.user.has_group('finance.group_finance_user'):
            raise UserError("Seuls les managers peuvent rejeter les demandes de modification.")
        
        self.write({
            'state': 'rejected',
            'approved_by': self.env.user.id,
            'response_date': fields.Datetime.now(),
        })
        
        # Send notification to requester
        self.message_post(
            body=f"Demande rejetée par {self.env.user.name}.",
            subject="Demande de modification rejetée",
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Demande rejetée',
                'message': 'La demande a été rejetée.',
                'type': 'warning',
                'sticky': False,
            }
        }
