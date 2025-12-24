from odoo import models, fields, api

class FinanceLogisticsTracking(models.Model):
    _name = 'finance.logistics.tracking'
    _description = 'Suivi Conteneurs (Finance)'
    _rec_name = 'entry_id'

    entry_id = fields.Many2one('logistique.entry', string='Conteneur / Entrée', required=True)
    
    # Related Fields (Read-only for display)
    container_id = fields.Many2one(related='entry_id.container_id', string='Conteneur', readonly=True)
    ste_id = fields.Many2one(related='entry_id.ste_id', string='Société', readonly=True)
    supplier_id = fields.Many2one(related='entry_id.supplier_id', string='Fournisseur', readonly=True)
    article_id = fields.Many2one(related='entry_id.article_id', string='Article', readonly=True)
    shipping_id = fields.Many2one(related='entry_id.shipping_id', string='Compagnie Maritime', readonly=True)
    week = fields.Char(related='entry_id.week', string='Semaine', readonly=True)
    invoice_number = fields.Char(related='entry_id.invoice_number', string='Facture', readonly=True)
    bl_number = fields.Char(related='entry_id.bl_number', string='BL', readonly=True)
    eta = fields.Date(related='entry_id.eta', string='ETA', readonly=True)
    weight = fields.Float(related='entry_id.weight', string='Poids', readonly=True)
    details = fields.Char(related='entry_id.details', string='Détails', readonly=True)
    free_time = fields.Integer(related='entry_id.free_time', string='Free Time', readonly=True)
    remarks = fields.Char(related='entry_id.remarks', string='Remarques', readonly=True)
    status = fields.Selection(related='entry_id.status', string='Status', readonly=True)

    # Writable Fields (Write back to original record)
    prov_number = fields.Char(related='entry_id.prov_number', string='N° Prov', readonly=False, store=True) # store=True sometimes helps with write-back in some versions but False is standard for proxy. We keep standard behavior first (False). Confirmed: Related fields are writable by default if not readonly=True.
    def_number = fields.Char(related='entry_id.def_number', string='N° Def', readonly=False)
