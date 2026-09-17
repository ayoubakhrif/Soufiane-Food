from odoo import models, fields, api

class LogisticsEntry(models.Model):
    _inherit = 'logistique.entry'

    dum = fields.Char(string='DUM')
    dum_date = fields.Date(string='Date DUM')
    exchange_rate = fields.Float(string='Taux de change', digits=(12, 4))
    
    amount_mad = fields.Float(
        string='Montant (MAD)',
        compute='_compute_amount_mad',
        store=True,
        digits=(16, 2)
    )
    
    vat = fields.Float(string='TVA')
    customs_duty = fields.Float(string='Droit de douane')
    
    customs_total = fields.Float(
        string='Droits total',
        compute='_compute_customs_total',
        store=True,
        digits=(16, 2)
    )
    
    transit_fees = fields.Float(string='Frais de transit')
    temsa = fields.Float(string='TEMSA')
    
    analysis_result = fields.Selection([
        ('pending', 'En cours'),
        ('ok', 'Conforme'),
        ('rejected', 'Non conforme'),
    ], string='Résultat Analyse', default='pending')
    
    douane_document_ids = fields.One2many(
        'douane.document',
        'entry_id',
        string='Documents Douane'
    )
    
    logistique_document_ids = fields.One2many(
        'logistique.entry.document',
        'entry_id',
        string='Documents Logistique'
    )

    @api.depends('amount_total', 'exchange_rate')
    def _compute_amount_mad(self):
        for rec in self:
            rec.amount_mad = rec.amount_total * rec.exchange_rate

    @api.depends('vat', 'customs_duty')
    def _compute_customs_total(self):
        for rec in self:
            rec.customs_total = rec.vat + rec.customs_duty

    def name_get(self):
        result = []
        for record in self:
            if record.dum:
                name = f"[{record.dum}] {record.bl_number or 'Sans BL'}"
            else:
                name = record.bl_number or f"Dossier Logistique #{record.id}"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('dum', operator, name), ('bl_number', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
