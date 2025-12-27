from odoo import models, fields, api

class FinanceLogisticsTracking(models.Model):
    _name = 'finance.logistics.tracking'
    _description = 'Suivi Dossiers Logistiques (Finance)'
    _rec_name = 'dossier_id'

    # Core reference - Dossier instead of individual entry
    dossier_id = fields.Many2one('logistique.dossier', string='Dossier / BL', required=True, readonly=True, ondelete='cascade')
    
    # Writable Fields - Finance manages provisional and definitive numbers
    prov_number = fields.Char(related='dossier_id.prov_number', string='N° Prov', readonly=False, store=True)
    def_number = fields.Char(related='dossier_id.def_number', string='N° Def', readonly=False, store=True)
    
    # Automatic display of dossier-related data (read-only)
    container_ids = fields.One2many(related='dossier_id.container_ids', string='Conteneurs', readonly=True)
    cheque_ids = fields.One2many(related='dossier_id.cheque_ids', string='Chèques', readonly=True)
    entry_ids = fields.One2many(related='dossier_id.entry_ids', string='Entrées Logistiques', readonly=True)
    
    # BL Number (from dossier)
    bl_number = fields.Char(related='dossier_id.name', string='N° BL', readonly=True, store=True)
    
    # Related Fields from logistics entries (aggregated or from first entry)
    # Note: If multiple entries exist, these show data from related entries
    # For simplicity, we can compute or use the first entry
    
    # Display fields - computed from related logistics entries
    ste_id = fields.Many2one('logistique.ste', string='Société', compute='_compute_entry_data', store=False)
    supplier_id = fields.Many2one('logistique.supplier', string='Fournisseur', compute='_compute_entry_data', store=False)
    article_id = fields.Many2one('logistique.article', string='Article', compute='_compute_entry_data', store=False)
    shipping_id = fields.Many2one('logistique.shipping', string='Compagnie Maritime', compute='_compute_entry_data', store=False)
    week = fields.Char(string='Semaine', compute='_compute_entry_data', store=False)
    invoice_number = fields.Char(string='Facture', compute='_compute_entry_data', store=False)
    eta = fields.Date(string='ETA', compute='_compute_entry_data', store=False)
    weight = fields.Float(string='Poids', compute='_compute_entry_data', store=False)
    details = fields.Char(string='Détails', compute='_compute_entry_data', store=False)
    free_time = fields.Integer(string='Free Time', compute='_compute_entry_data', store=False)
    remarks = fields.Char(string='Remarques', compute='_compute_entry_data', store=False)
    status = fields.Selection([
        ('in_progress', 'En cours'),
        ('get_out', 'Get Out'),
        ('closed', 'Cloturé'),
    ], string='Status', compute='_compute_entry_data', store=False)
    
    # Financial & Audit Fields
    price_unit = fields.Float(string='P.U', compute='_compute_entry_data', store=False)
    amount_total = fields.Float(string='Total', compute='_compute_entry_data', store=False)
    user_id = fields.Many2one('res.users', string='Saisi par', compute='_compute_entry_data', store=False)

    @api.depends('dossier_id.entry_ids')
    def _compute_entry_data(self):
        """Compute display fields from the first logistics entry of the dossier."""
        for rec in self:
            first_entry = rec.dossier_id.entry_ids[:1]
            if first_entry:
                rec.ste_id = first_entry.ste_id
                rec.supplier_id = first_entry.supplier_id
                rec.article_id = first_entry.article_id
                rec.shipping_id = first_entry.shipping_id
                rec.week = first_entry.week
                rec.invoice_number = first_entry.invoice_number
                rec.eta = first_entry.eta
                rec.weight = first_entry.weight
                rec.details = first_entry.details
                rec.free_time = first_entry.free_time
                rec.remarks = first_entry.remarks
                rec.status = first_entry.status
                # New fields
                rec.price_unit = first_entry.price_unit
                rec.amount_total = first_entry.amount_total
                rec.user_id = first_entry.user_id
            else:
                # No entries yet - set defaults
                rec.ste_id = False
                rec.supplier_id = False
                rec.article_id = False
                rec.shipping_id = False
                rec.week = False
                rec.invoice_number = False
                rec.eta = False
                rec.weight = 0.0
                rec.details = False
                rec.free_time = 0
                rec.remarks = False
                rec.status = False
                # New fields
                rec.price_unit = 0.0
                rec.amount_total = 0.0
                rec.user_id = False

    # Constraints
    _sql_constraints = [
        ('unique_dossier_id', 'unique(dossier_id)', 
         'Un enregistrement de suivi existe déjà pour ce dossier.')
    ]
