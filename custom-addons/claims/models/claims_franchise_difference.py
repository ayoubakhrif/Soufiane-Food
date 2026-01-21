from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class ClaimsFranchiseDifference(models.Model):
    _name = 'claims.franchise.difference'
    _description = 'Franchise Difference Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'bl_id'

    # ==========================
    # 1. Main Data
    # ==========================
    bl_id = fields.Many2one(
        'logistique.entry',
        string='BL Reference',
        required=True,
        readonly=False, # Editable only in initial state (handled in view)
        domain="[('bl_number', '!=', False)]",
        tracking=True
    )
    claim_date = fields.Date(string='Date de création', default=fields.Date.context_today, readonly=True)

    # Auto-filled (Read-only, from BL)
    company_id = fields.Many2one(related='bl_id.ste_id', string='Société', readonly=True, store=True)
    supplier_id = fields.Many2one(related='bl_id.supplier_id', string='Supplier', readonly=True, store=True)
    origin = fields.Char(related='bl_id.origin', string='Origin', readonly=True, store=True)
    article_id = fields.Many2one(related='bl_id.article_id', string='Article', readonly=True, store=True)
    lot = fields.Char(related='bl_id.lot', string='LOT', readonly=True, store=True)
    invoice_number = fields.Char(related='bl_id.invoice_number', string='Invoice Number', readonly=True, store=True)

    # ==========================
    # 2. Franchise Specific Fields
    # ==========================
    franchise_confirmed = fields.Float(
        string='Franchise Confirmed',
        required=True,
        tracking=True
    )
    franchise_found = fields.Float(
        string='Franchise Found',
        required=True,
        tracking=True
    )
    
    franchise_difference = fields.Float(
        string='Difference',
        compute='_compute_difference',
        store=True,
        readonly=True
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
    # 5. Logic & Constraints
    # ==========================

    @api.depends('franchise_confirmed', 'franchise_found')
    def _compute_difference(self):
        for rec in self:
            rec.franchise_difference = rec.franchise_found - rec.franchise_confirmed

    @api.constrains('franchise_confirmed', 'franchise_found')
    def _check_difference(self):
        for rec in self:
            if rec.franchise_confirmed == rec.franchise_found:
                 raise ValidationError("No franchise difference detected. A claim cannot be created (Confirmed == Found).")

    # ==========================
    # 6. Workflow Actions
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
        self.write({'state': 'resolved'})

    def action_close(self):
        """Resolved -> Closed"""
        self._check_responsibility()
        self.write({'state': 'closed'})

    def _check_responsibility(self):
        """Ensure only the responsible user can proceed."""
        for rec in self:
            if rec.responsible_id and rec.responsible_id != self.env.user:
                raise UserError("You are not the responsible person for this claim. Only %s can proceed." % rec.responsible_id.name)
