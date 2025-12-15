from odoo import models, fields, api, exceptions

class FinanceDeletionRequest(models.Model):
    _name = 'finance.deletion.request'
    _description = 'Demande de suppression'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'res_id'

    user_id = fields.Many2one('res.users', string='Demandé par', default=lambda self: self.env.user, readonly=True, required=True)
    request_date = fields.Datetime(string='Date de demande', default=fields.Datetime.now, readonly=True)
    
    model = fields.Char(string='Modèle', required=True, readonly=True)
    res_id = fields.Integer(string='ID Enregistrement', required=True, readonly=True)
    record_name = fields.Char(string='Enregistrement', compute='_compute_record_name', store=True)
    reason = fields.Text(string='Motif de suppression', tracking=True)
    
    state = fields.Selection([
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté')
    ], string='État', default='pending', tracking=True, readonly=True)

    @api.model
    def create(self, vals):
        record = super(FinanceDeletionRequest, self).create(vals)
        record._schedule_activity_for_managers()
        return record

    def _schedule_activity_for_managers(self):
        """Schedules a todo activity for all finance managers."""
        # Find the group
        group_manager = self.env.ref('finance.group_finance_user', raise_if_not_found=False)
        if not group_manager:
            return

        # Find users in the group
        managers = group_manager.users
        
        # Activity details
        activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
        summary = f"Nouvelle demande de suppression: {self.record_name}"
        note = f"L'utilisateur {self.user_id.name} a demandé la suppression de {self.record_name}. Raison: {self.reason or 'Non spécifiée'}"
        
        # Create activity for each manager
        for manager in managers:
            # Avoid self-notification if manager creates the request (though minimal risk as managers delete directly)
            if manager == self.env.user:
                continue
                
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=manager.id,
                summary=summary,
                note=note,
                date_deadline=fields.Date.today()
            )

    @api.depends('model', 'res_id')
    def _compute_record_name(self):
        for rec in self:
            if rec.model and rec.res_id:
                try:
                    record = self.env[rec.model].sudo().browse(rec.res_id)
                    rec.record_name = record.display_name or f"{rec.model},{rec.res_id}"
                except:
                    rec.record_name = f"{rec.model},{rec.res_id}"
            else:
                rec.record_name = "N/A"

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

    def action_reject(self):
        self.ensure_one()
        self.state = 'rejected'
        self.message_post(body="Demande rejetée.")
