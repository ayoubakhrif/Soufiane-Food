from odoo import models, fields, api

class AchatEntry(models.Model):
    _inherit = 'logistique.entry'

    # --- ACHAT FIELDS (Readonly for Logistique users via View) ---
    
    # NOTE: Some fields might already exist in logistique.entry. We override/ensure they are here.
    # User listed: ETA, Week, Invoice, Company, Supplier, Shipping, Article, Details, Weight, Unit Price, Total, Incoterm, Free Time, Doc Status.
    
    # Reuse existing fields if present, define new ones if not.
    # logistique.entry ALREADY HAS: week, ste_id, supplier_id, invoice_number, article_id, details, weight, price_unit, amount_total, incoterm, free_time, shipping_id, eta, doc_status, remarks.
    
    # We add Workflow State
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validé Achat'),
        ('in_progress', 'En cours'),
        ('closed', 'Cloturé'),
    ], string='État Workflow', default='draft', tracking=True)

    # We ensure these fields are tracked
    eta = fields.Date(tracking=True)
    invoice_number = fields.Char(tracking=True)
    price_unit = fields.Float(tracking=True)
    amount_total = fields.Float(tracking=True)
    
    # Validation Logic
    def action_validate_achat(self):
        for rec in self:
            rec.state = 'validated'

