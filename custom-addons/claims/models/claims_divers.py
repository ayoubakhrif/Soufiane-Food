from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class ClaimsDivers(models.Model):
    _name = 'claims.divers'
    _description = 'Divers Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'bl_id'

    # ==========================
    # 1. Main Data
    # ==========================
    
    def action_print_report(self):
        for rec in self:
            if rec.amount_due <= 0:
                raise UserError("Cannot print report: Amount Due must be greater than 0.")
            if rec.state == 'initial':
                raise UserError("Cannot print report: Claim is in Initial state.")
            if rec.responsible_id and rec.responsible_id != self.env.user:
                raise UserError("You cannot print this report. Only the responsible user (%s) can print it." % rec.responsible_id.name)
        # Note: Report action needs to be defined if required for divers
        # return self.env.ref('claims.action_report_claims_divers').report_action(self)
        raise UserError("PDF Report is not yet configured for Divers Claims.")
        
    bl_id = fields.Many2one(
        'logistique.entry',
        string='BL Reference',
        required=True,
        readonly=True,
        domain="[('bl_number', '!=', False)]",
        tracking=True
    )
    claim_date = fields.Date(string='Date de création', default=fields.Date.context_today, readonly=True)
    date_received = fields.Date(string='Date Received', readonly=True, tracking=True)
    date_waiting = fields.Date(string='Date Waiting', readonly=True, tracking=True)
    date_refused = fields.Date(string='Date Refused', readonly=True, tracking=True)
    date_resolved = fields.Date(string='Date Resolved', readonly=True, tracking=True)
    date_closed = fields.Date(string='Date Closed', readonly=True, tracking=True)

    # Auto-filled (Read-only, from BL)
    company_id = fields.Many2one(related='bl_id.ste_id', string='Société', readonly=True, store=True)
    supplier_id = fields.Many2one(related='bl_id.supplier_id', string='Supplier', readonly=True, store=True)
    origin = fields.Char(related='bl_id.origin_id.name', string='Origin', readonly=True, store=True)
    article_id = fields.Many2one(related='bl_id.article_id', string='Article', readonly=True, store=True)
    lot = fields.Char(related='bl_id.lot', string='LOT', readonly=True, store=True)
    invoice_number = fields.Char(related='bl_id.invoice_number', string='Invoice Number', readonly=True, store=True)

    # ==========================
    # 2. User-entered Fields
    # ==========================
    
    company_logo = fields.Binary(compute='_compute_company_logo', string='Logo Société')

    def _compute_company_logo(self):
        for rec in self:
            # Sudo to bypass access rights to core.ste
            if rec.bl_id and rec.bl_id.ste_id and rec.bl_id.ste_id.core_ste_id:
                rec.company_logo = rec.bl_id.ste_id.core_ste_id.sudo().image_1920
            else:
                rec.company_logo = False

    charge_ids = fields.One2many(
        'claims.divers.charge',
        'claim_id',
        string='Charges'
    )

    amount_due = fields.Float(
        string='Amount Due',
        compute='_compute_amount_due',
        store=True,
        tracking=True
    )

    @api.depends('charge_ids.amount')
    def _compute_amount_due(self):
        for rec in self:
            rec.amount_due = sum(charge.amount for charge in rec.charge_ids)

    comment = fields.Text(string='Old Comment (Deprecated)')
    
    comment_creator = fields.Text(
        string='Commentaire (Créateur)',
        help="Commentaire du créateur de la réclamation. Toujours modifiable."
    )
    comment_responsible = fields.Text(
        string='Commentaire (Responsable)',
        help="Commentaire du responsable. Toujours modifiable."
    )

    # ==========================
    # 3. Creator & Responsibility
    # ==========================
    create_uid = fields.Many2one('res.users', string='Creator', readonly=True)
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsible',
        readonly=True,
        tracking=True
    )

    # ==========================
    # 4. Workflow & States
    # ==========================
    state = fields.Selection([
        ('initial', 'Initial'),
        ('received', 'Received'),
        ('waiting', 'Waiting Supplier Response'),
        ('refused', 'Refusé'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], string='Status', default='initial', required=True, tracking=True)

    # ==========================
    # 5. Workflow Actions
    # ==========================

    def action_receive(self):
        """Initial -> Received. Sets current user as responsible."""
        for rec in self:
            rec.responsible_id = self.env.user
            rec.state = 'received'
            rec.date_received = fields.Date.context_today(self)

    def action_send_supplier(self):
        """Received -> Waiting"""
        self._check_responsibility()
        self.write({
            'state': 'waiting',
            'date_waiting': fields.Date.context_today(self)
        })

    def action_resolve(self):
        """Waiting -> Resolved"""
        self._check_responsibility()
        if not self.evidence_link:
             raise ValidationError("You must provide an evidence link before resolving this claim.")
        self.write({
            'state': 'resolved',
            'date_resolved': fields.Date.context_today(self)
        })

    def action_close(self):
        """Resolved -> Closed. Admin only."""
        if not self.env.user.has_group('claims.group_claims_manager'):
            raise UserError("Only Administrators can close claims.")
        self.write({
            'state': 'closed',
            'date_closed': fields.Date.context_today(self)
        })

    def action_refuse(self):
        """Waiting -> Refused. Admin only."""
        if not self.env.user.has_group('claims.group_claims_manager'):
            raise UserError("Only Administrators can refuse claims.")
        self.write({
            'state': 'refused',
            'date_refused': fields.Date.context_today(self)
        })

    def _check_responsibility(self):
        """Ensure only the responsible user can proceed."""
        for rec in self:
            if rec.responsible_id and rec.responsible_id != self.env.user:
                raise UserError("You are not the responsible person for this claim. Only %s can proceed." % rec.responsible_id.name)

    # ==========================
    # 7. Evidence Logic
    # ==========================
    evidence_link = fields.Char(string='Evidence Link', help="Link to proof documents (emails, reports, etc.)")
    can_see_evidence = fields.Boolean(compute='_compute_can_see_evidence')

    @api.depends('responsible_id')
    def _compute_can_see_evidence(self):
        is_admin = self.env.user.has_group('claims.group_claims_manager') or self.env.user.has_group('base.group_system')
        for rec in self:
            rec.can_see_evidence = is_admin or (rec.responsible_id == self.env.user)

    def action_open_evidence(self):
        self.ensure_one()
        if self.evidence_link:
            return {
                'type': 'ir.actions.act_url',
                'url': self.evidence_link,
                'target': 'new',
            }

class ClaimsDiversCharge(models.Model):
    _name = 'claims.divers.charge'
    _description = 'Divers Claim Charge'

    claim_id = fields.Many2one('claims.divers', string='Claim', required=True, ondelete='cascade')
    name = fields.Char(string='Type de Charge', required=True)
    amount = fields.Float(string='Amount', required=True)
