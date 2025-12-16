from odoo import models, fields, api, exceptions

class FinanceDeletionRequest(models.Model):
    _name = 'finance.deletion.request'
    _description = 'Demande de suppression'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'res_id'
    _order = 'request_date desc, id desc'

    user_id = fields.Many2one('res.users', string='Demandé par', default=lambda self: self.env.user, readonly=True, required=True)
    request_date = fields.Datetime(string='Date de demande', default=fields.Datetime.now, readonly=True)
    
    model = fields.Char(string='Modèle', required=True, readonly=True)
    res_id = fields.Integer(string='ID Enregistrement', required=True, readonly=True)
    record_name = fields.Char(string='Enregistrement', compute='_compute_record_name', store=True)
    reason = fields.Text(string='Motif de suppression', tracking=True, required=True)
    
    state = fields.Selection([
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté')
    ], string='État', default='pending', tracking=True, readonly=True)

    @api.depends('model', 'res_id')
    def _compute_record_name(self):
        for rec in self:
            if rec.model and rec.res_id:
                try:
                    record = self.env[rec.model].sudo().browse(rec.res_id)
                    if record.exists():
                        rec.record_name = record.display_name
                    else:
                        rec.record_name = f"{rec.model},{rec.res_id}"
                except:
                    rec.record_name = f"{rec.model},{rec.res_id}"
            else:
                rec.record_name = "N/A"

    @api.model
    def create(self, vals):
        record = super(FinanceDeletionRequest, self).create(vals)
        # Schedule activity for Finance Managers
        group_finance_user = self.env.ref('finance.group_finance_user')
        if group_finance_user:
            managers = group_finance_user.users
            for manager in managers:
                record.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=manager.id,
                    summary=f'Demande de suppression de {record.user_id.name}',
                    note=f'Demande de suppression pour {record.record_name}. Motif: {record.reason or "Non spécifié"}'
                )
        return record

    def action_approve(self):
        self.ensure_one()
        if self.state != 'pending':
            return
            
        record = self.env[self.model].sudo().browse(self.res_id)
        if record.exists():
            # Perform deletion as sudo (bypass access rights for employee, relies on manager's approval)
            # Check if current user is manager is handled by access rights on this model/button
            record.sudo().unlink()
        
        self.state = 'approved'
        self.message_post(body="Demande approuvée et enregistrement supprimé.")
        self.activity_feedback(['mail.mail_activity_data_todo'])

    def action_reject(self):
        self.ensure_one()
        self.state = 'rejected'
        self.message_post(body="Demande rejetée.")
        self.activity_feedback(['mail.mail_activity_data_todo'])
