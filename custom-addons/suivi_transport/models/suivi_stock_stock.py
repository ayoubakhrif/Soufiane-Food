from odoo import models, fields, tools, api

class SuiviStockStock(models.Model):
    _name = 'suivi.stock.stock'
    _description = 'Stock Suivi Transport (Aggregation)'
    _auto = False
    _log_access = False
    _order = 'quantity desc, product_id'

    product_id = fields.Many2one('suivi.produit', string='Produit', readonly=True)
    lot = fields.Char(string='Lot', readonly=True)
    dum = fields.Char(string='DUM', readonly=True)
    ville = fields.Selection([
        ('casa', 'Casa'),
    ], string='Ville', readonly=True)
    
    quantity = fields.Float(string='Quantité', readonly=True)
    weight = fields.Float(string='Poids (Kg)', readonly=True)
    calibre = fields.Char(string='Calibre', readonly=True)
    
    image_1920 = fields.Image(related='product_id.image_1920', readonly=True)
    write_date = fields.Datetime(string='Last Update', readonly=True)
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    scan_dum = fields.Char(string='Scan DUM (Drive)', readonly=True)
    
    total_weight = fields.Float(string='Tonnage', readonly=True)

    @api.depends('product_id.name', 'lot', 'dum', 'quantity')
    def _compute_display_name(self):
        for rec in self:
            name_parts = [rec.product_id.name] if rec.product_id else ['Inconnu']
            if rec.lot:
                name_parts.append(f"Lot: {rec.lot}")
            if rec.dum:
                name_parts.append(f"DUM: {rec.dum}")
            
            qty_str = f"{rec.quantity} ({(rec.quantity * rec.weight):.2f}Kg)"
            name_parts.append(f"Dispo: {qty_str}")
                
            rec.display_name = ' - '.join(name_parts)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None, **kwargs):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', ('product_id.name', operator, name), ('lot', operator, name), ('dum', operator, name)]
        order = kwargs.get('order', self._order)
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid, order=order)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    min(m.id) as id,
                    m.product_id,
                    m.lot,
                    m.dum,
                    m.ville,
                    m.calibre,
                    m.weight,
                    sum(m.qty) as quantity,
                    (sum(m.qty) * m.weight) as total_weight,
                    max(m.date) as write_date,
                    min(m.date) as create_date,
                    min(m.date) as date,
                    max(m.scan_dum) as scan_dum
                FROM
                    suivi_stock_move m
                WHERE
                    m.state = 'done'
                GROUP BY
                    m.product_id, m.lot, m.dum, m.ville, m.weight, m.calibre
            )
        """ % self._table)
