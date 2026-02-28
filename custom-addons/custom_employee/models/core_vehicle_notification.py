from odoo import models, fields, api, exceptions
from dateutil.relativedelta import relativedelta

class CoreVehicleNotification(models.Model):
    _name = 'core.vehicle.notification'
    _description = 'Notification Véhicule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _rec_name = 'vehicle_id'

    vehicle_id = fields.Many2one(
        'core.vehicle',
        string='Véhicule',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    notification_type = fields.Selection([
        ('expiration', 'Expiration de document'),
        ('missing', 'Document absent'),
    ], string='Type', required=True, index=True)
    
    document_id = fields.Many2one(
        'core.vehicle.document',
        string='Document',
        ondelete='cascade',
        index=True,
        help='Document concerné (pour type expiration)'
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        index=True
    )
    
    state = fields.Selection([
        ('pending', 'En attente'),
        ('treated', 'Traité'),
    ], string='État', default='pending', required=True, index=True)
    
    message = fields.Text(string='Message')
    
    # Related fields for display
    expiration_date = fields.Date(
        string="Date d'expiration",
        related='document_id.expiration_date',
        readonly=True
    )
    document_type = fields.Selection(
        related='document_id.doc_type',
        string='Type de document',
        readonly=True
    )

    _sql_constraints = [
        ('unique_pending_notification',
         'unique(vehicle_id, document_id, notification_type, state)',
         'Une notification en attente existe déjà pour ce document !')
    ]

    @api.model
    def create(self, vals):
        notification = super(CoreVehicleNotification, self).create(vals)
        if notification.notification_type == 'expiration' and notification.state == 'pending':
            self._create_deadline_activity(notification)
        return notification

    def _create_deadline_activity(self, notification):
        """Create Activity alert 7 days BEFORE document expiration"""

        expiry = notification.document_id.expiration_date
        if not expiry:
            return

        today = fields.Date.today()
        alert_date = expiry - relativedelta(days=7)

        # From J-7 onward, force activity into clock
        deadline = today if today >= alert_date else alert_date

        model_id = self.env['ir.model']._get('core.vehicle.notification').id
        if not model_id:
            return

        activity_type_id = self.env.ref('mail.mail_activity_data_todo').id

        # Target all internal users (Employees/Managers of custom_employee)
        # Assuming we want to notify relevant groups. 
        # User request: "Visible to all internal users of the module"
        group_user = self.env.ref('custom_employee.group_core_employee_user')
        group_manager = self.env.ref('custom_employee.group_core_employee_manager')
        target_users = group_user.users | group_manager.users

        activities = []
        for user in target_users:
            if not user.share:
                activities.append({
                    'res_model_id': model_id,
                    'res_model': 'core.vehicle.notification',
                    'res_id': notification.id,
                    'activity_type_id': activity_type_id,
                    'summary': 'Document Véhicule expire bientôt',
                    'note': notification.message or "Le document doit être renouvelé avant expiration.",
                    'date_deadline': deadline,
                    'user_id': user.id,
                })

        if activities:
            self.env['mail.activity'].create(activities)

    @api.constrains('vehicle_id', 'document_id', 'notification_type', 'state')
    def _check_unique_pending(self):
        """Ensure only one pending notification per vehicle/document/type"""
        for record in self:
            if record.state == 'pending':
                existing = self.search([
                    ('vehicle_id', '=', record.vehicle_id.id),
                    ('document_id', '=', record.document_id.id),
                    ('notification_type', '=', record.notification_type),
                    ('state', '=', 'pending'),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise exceptions.ValidationError(
                        'Une notification en attente existe déjà pour ce document.'
                    )

    def action_mark_treated(self):
        """Mark notification as treated and complete related activity"""
        for record in self:
            record.write({'state': 'treated'})
            # Complete ALL activities
            record.activity_ids.action_done()

    @api.model
    def _check_all_vehicle_document_expirations(self):
        """
        Centralized notification creation logic (called by cron).
        Checks all vehicle documents and creates notifications for:
        - Documents expiring in <= 7 days
        - Documents already expired
        """
        today = fields.Date.today()
        documents = self.env['core.vehicle.document'].search([
            ('expiration_date', '!=', False)
        ])
        
        for doc in documents:
            days_until_expiration = (doc.expiration_date - today).days
            
            # Create notification if expires in <= 7 days or already expired
            if days_until_expiration <= 7:
                # Check if pending notification already exists
                existing = self.search([
                    ('vehicle_id', '=', doc.vehicle_id.id),
                    ('document_id', '=', doc.id),
                    ('notification_type', '=', 'expiration'),
                    ('state', '=', 'pending')
                ])
                
                if not existing:
                    doc_type_label = dict(doc._fields['doc_type'].selection).get(doc.doc_type, doc.doc_type)
                    message = f"Le document {doc_type_label} du véhicule {doc.vehicle_id.matricule} expire le {doc.expiration_date.strftime('%d/%m/%Y')} (J-{days_until_expiration})"
                    
                    self.create({
                        'vehicle_id': doc.vehicle_id.id,
                        'document_id': doc.id,
                        'notification_type': 'expiration',
                        'date': today,
                        'message': message,
                    })
