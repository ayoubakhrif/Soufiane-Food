from odoo import models, fields, api

class SuiviStockMove(models.Model):
    _name = 'suivi.stock.move'
    _description = 'Mouvement de Stock Suivi Transport'
    _order = 'date desc, id desc'

    product_id = fields.Many2one('suivi.produit', string='Produit', required=True)
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    ville = fields.Selection([
        ('casa', 'Casa'),
    ], string='Ville', default='casa', required=True)
    
    qty = fields.Float(string='Quantité', required=True)
    weight = fields.Float(string='Poids (Kg)')
    calibre = fields.Char(string='Calibre')
    
    move_type = fields.Selection([
        ('entry', 'Entrée'),
        ('cancel_entry', 'Annulation Entrée'),
        ('exit', 'Sortie'),
        ('cancel_exit', 'Annulation Sortie'),
        ('return', 'Retour'),
    ], string='Type de Mouvement', required=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Validé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True)
    
    date = fields.Datetime(string='Date', required=True, default=fields.Datetime.now)
    reference = fields.Char(string='Référence')
    
    scan_dum = fields.Char(string='Scan DUM (Drive)')
    
    fournisseur_id = fields.Many2one('suivi.fournisseur', string='Fournisseur')
    chauffeur_id = fields.Many2one('suivi.chauffeur', string='Chauffeur')
    
    res_model = fields.Char(string='Modèle Source')
    res_id = fields.Integer(string='ID Source')
    
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)

    @api.depends('qty', 'weight')
    def _compute_tonnage(self):
        for rec in self:
            rec.tonnage = rec.qty * rec.weight
