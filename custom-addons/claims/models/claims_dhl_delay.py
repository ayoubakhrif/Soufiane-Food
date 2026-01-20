from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date

class ClaimsDHLDelay(models.Model):
    _name = 'claims.dhl.delay'
    _description = 'DHL Delay Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'bl_id'

    # ==========================
    # 1. Main Data
    # ==========================
    bl_id = fields.Many2one(
        'logistique.entry',
        string='BL Reference',
        required=True,
        readonly=True,
        states={'initial': [('readonly', False)]},
        domain="[('bl_number', '!=', False)]",
        tracking=True
    )

    # Auto-filled (Read-only, from BL)
    company_id = fields.Many2one(related='bl_id.ste_id', string='Société', readonly=True, store=True)
    supplier_id = fields.Many2one(related='bl_id.supplier_id', string='Supplier', readonly=True, store=True)
    origin = fields.Char(related='bl_id.origin', string='Origin', readonly=True, store=True)
    article_id = fields.Many2one(related='bl_id.article_id', string='Article', readonly=True, store=True)
    lot = fields.Char(related='bl_id.lot', string='LOT', readonly=True, store=True)
    invoice_number = fields.Char(related='bl_id.invoice_number', string='Invoice Number', readonly=True, store=True)

    # ==========================
    # 2. User-entered Fields
    # ==========================
    eta_planned = fields.Date(
        string='ETA Planned',
        required=True,
        readonly=True,
        states={'initial': [('readonly', False)]},
        tracking=True
    )
    eta_dhl = fields.Date(
        string='ETA DHL',
        required=True,
        readonly=True,
        states={'initial': [('readonly', False)]},
        tracking=True
    )
    dhl_delay = fields.Integer(
        string='DHL Delay (Days)',
        compute='_compute_dhl_delay',
        store=True,
        readonly=True
    )
    comment = fields.Text(
        string='Comment',
        readonly=True,
        states={'initial': [('readonly', False)]}
    )
    amount_due = fields.Float(
        string='Amount Due',
        readonly=True,
        states={'initial': [('readonly', False)]},
        tracking=True
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
    # 5. Logic
    # ==========================

    @api.depends('eta_planned', 'eta_dhl')
    def _compute_dhl_delay(self):
        for rec in self:
            if rec.eta_planned and rec.eta_dhl:
                delta = rec.eta_dhl - rec.eta_planned
                rec.dhl_delay = delta.days
            else:
                rec.dhl_delay = 0

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
