from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class ClaimsQuality(models.Model):
    _name = 'claims.quality'
    _description = 'Quality Claim'
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
        return self.env.ref('claims.action_report_claims_quality').report_action(self)

    bl_id = fields.Many2one(
        'logistique.entry',
        string='BL Reference',
        required=True,
        readonly=True,
        domain="[('bl_number', '!=', False)]",
        tracking=True
    )
    claim_date = fields.Date(string='Date de création', default=fields.Date.context_today, readonly=True)

    # Auto-filled (Read-only, from BL)
    company_id = fields.Many2one(related='bl_id.ste_id', string='Société', readonly=True, store=True)
    supplier_id = fields.Many2one(related='bl_id.supplier_id', string='Supplier', readonly=True, store=True)
    origin = fields.Char(related='bl_id.origin_id.name', string='Origin', readonly=True, store=True)
    article_id = fields.Many2one(related='bl_id.article_id', string='Article', readonly=True, store=True)
    lot = fields.Char(related='bl_id.lot', string='LOT', readonly=True, store=True)
    invoice_number = fields.Char(related='bl_id.invoice_number', string='Invoice Number', readonly=True, store=True)

    # Sudo Logo
    company_logo = fields.Binary(compute='_compute_company_logo', string='Logo Société')

    def _compute_company_logo(self):
        for rec in self:
            if rec.bl_id and rec.bl_id.ste_id and rec.bl_id.ste_id.core_ste_id:
                rec.company_logo = rec.bl_id.ste_id.core_ste_id.sudo().image_1920
            else:
                rec.company_logo = False

    # ==========================
    # 2. Quality Specific Fields
    # ==========================
    qc_url = fields.Char(
        string='Quality Control Folder Link',
        required=True,
        tracking=True,
        help="Link to the quality control inspection folder/document."
    )

    amount_due = fields.Float(
        string='Amount Due',
        tracking=True
    )

    # Comments (Always Editable)
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

    def action_send_supplier(self):
        """Received -> Waiting"""
        self._check_responsibility()
        self.write({'state': 'waiting'})

    def action_resolve(self):
        """Waiting -> Resolved"""
        self._check_responsibility()
        if not self.evidence_link:
             raise ValidationError("You must provide an evidence link before resolving this claim.")
        self.write({'state': 'resolved'})

    def action_close(self):
        """Resolved -> Closed"""
        self._check_responsibility()
        if not self.env.user.has_group('claims.group_claims_manager'):
            raise UserError("Only Administrators can close claims.")
        self.write({'state': 'closed'})

    def _check_responsibility(self):
        """Ensure only the responsible user can proceed."""
        for rec in self:
            if rec.responsible_id and rec.responsible_id != self.env.user:
                raise UserError("You are not the responsible person for this claim. Only %s can proceed." % rec.responsible_id.name)

    # ==========================
    # 6. Evidence & QC Link
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

    def action_open_qc_url(self):
        self.ensure_one()
        if self.qc_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.qc_url,
                'target': 'new',
            }
