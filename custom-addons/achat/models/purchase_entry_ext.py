from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta

class LogisticsEntry(models.Model):
    _inherit = 'logistique.entry'

    contract_id = fields.Many2one('achat.contract', string='Contract', domain="[('state', '=', 'open')]")
    free_time_negotiated = fields.Integer(string='Negotiated Free Time')

    is_non_change = fields.Boolean(string='Non Changé', default=False,
                                   help='Cocher si le dossier n\'a pas encore été changé')

    date_booking = fields.Date(string='Date of Booking')
    date_docs_received = fields.Date(string='Date Documents Received')
    date_docs_confirmed = fields.Date(string='Date Documents Confirmed')

    origin_id = fields.Many2one(
        'achat.origin',
        string='Origin'
    )

    
    # Document Link
    document_ids = fields.One2many('logistique.entry.document', 'entry_id', string='Documents')

    display_name = fields.Char(compute='_compute_display_name') # Just to ensure we have it if needed

    eta_this_week = fields.Boolean(
        string='ETA cette semaine',
        compute='_compute_eta_this_week',
        store=True,
        help='True if ETA <= next Thursday (inclusive) and port_status is on_port',
    )

    @api.depends('eta', 'port_status')
    def _compute_eta_this_week(self):
        today = date.today()
        days_to_thursday = (3 - today.weekday()) % 7
        next_thursday = today + timedelta(days=days_to_thursday)
        for rec in self:
            rec.eta_this_week = (
                rec.port_status == 'on_port'
                and bool(rec.eta)
                and rec.eta <= next_thursday
            )

    calendar_label = fields.Char(string='Label Calendrier', compute='_compute_calendar_label')

    @api.depends('supplier_id.name', 'article_id.name', 'ste_id.name', 'amount_total')
    def _compute_calendar_label(self):
        for rec in self:
            supplier = rec.supplier_id.name or ''
            article = rec.article_id.name or ''
            ste = rec.ste_id.name or ''
            total = rec.amount_total or 0.0
            # Format total with space as thousands separator
            total_str = "{:,.2f}".format(total).replace(",", " ")
            rec.calendar_label = f"{supplier} - {article} - {ste} - {total_str} USD"

    @api.depends('calendar_label', 'bl_number')
    def _compute_display_name(self):
        for rec in self:
            if rec.calendar_label:
                rec.display_name = rec.calendar_label
            else:
                rec.display_name = rec.bl_number or "Nouveau"

    @api.constrains('bl_number', 'contract_id')
    def _check_bl_contract_unique(self):
        """Prevent duplicate BL numbers for the same contract"""
        for rec in self:
            if rec.bl_number and rec.contract_id:
                duplicate = self.search([
                    ('id', '!=', rec.id),
                    ('bl_number', '=', rec.bl_number),
                    ('contract_id', '=', rec.contract_id.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f"The BL '{rec.bl_number}' exists already for this contract '{rec.contract_id.name}'.\n"
                        f"The same BL number cannot be used twice for the same contract."
                    )

    def action_confirm_purchase(self):
        # FIX: Allow regular purchase users to confirm too
        if not self.env.user.has_group('achat.group_purchase_user'):
            raise ValidationError("Only Purchase Users/Managers can confirm a dossier.")
        self.write({'purchase_state': 'confirmed'})

    def action_reset_to_initial(self):
        """Admin-only: Reset purchase state back to Initial."""
        self.write({'purchase_state': 'initial'})

    def action_reset_to_draft(self):
        """Admin-only: Reset purchase state back to Draft."""
        self.write({'purchase_state': 'draft'})

    article_id = fields.Many2one('achat.article', string='Article')
    details = fields.Char(string='Details')

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        if self.contract_id:
            self.contract_num = self.contract_id.name
            self.supplier_id = self.contract_id.supplier_id
            self.ste_id = self.contract_id.ste_id
            self.article_id = self.contract_id.article_id
            self.incoterm = self.contract_id.incoterm
            self.details = self.contract_id.details

            self.origin_id = self.contract_id.origin_id
            self.free_time_negotiated = self.contract_id.free_time_negotiated
            # Pre-fill actual free time with negotiated value
            self.free_time = self.contract_id.free_time_negotiated
            if self.contract_id.weight_total:
                self.weight = self.contract_id.weight_total # Optional sync, user might update per shipment
