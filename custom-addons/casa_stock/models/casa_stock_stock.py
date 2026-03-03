from odoo import models, fields, api, tools

class CasaStockStock(models.Model):
    _name = 'casa.stock.stock'
    _description = 'Stock Casa (Aggregation)'
    _auto = False
    _log_access = False
    _order = 'product_id'

    product_id = fields.Many2one('casa.product', string='Produit', readonly=True)
    lot = fields.Char(string='Lot', readonly=True)
    dum = fields.Char(string='DUM', readonly=True)
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville', readonly=True)
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock Casa'),
    ], string='Frigo', readonly=True)
    ste_id = fields.Many2one('casa.ste', string='Société', readonly=True)
    
    quantity = fields.Float(string='Quantité', readonly=True)
    weight = fields.Float(string='Poids (Kg)', readonly=True)
    calibre = fields.Char(string='Calibre', readonly=True)
    price = fields.Float(string='Dernier Prix (Achat)', readonly=True)
    mt_achat = fields.Float(string='Montant achat estimé', readonly=True)
    average_sale_price = fields.Float(string='P.V. Moyen', readonly=True)
    image_1920 = fields.Image(related='product_id.image_1920', readonly=True)
    write_date = fields.Datetime(string='Last Update', readonly=True)
    create_date = fields.Datetime(string='Creation Date', readonly=True)

    total_weight = fields.Float(string='Poids Total', readonly=True)

    def name_get(self):
        result = []
        for rec in self:
            name_parts = [rec.product_id.name]
            if rec.lot:
                name_parts.append(f"Lot: {rec.lot}")
            if rec.dum:
                name_parts.append(f"DUM: {rec.dum}")
            if rec.price:
                name_parts.append(f"{rec.price} MAD")
            if rec.create_date:
                name_parts.append(rec.create_date.strftime('%Y-%m-%d'))
                
            result.append((rec.id, ' - '.join(name_parts)))
        return result

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
                    m.frigo,
                    m.ste_id,
                    m.calibre,
                    m.weight,
                    m.price_purchase as price,
                    sum(m.qty) as quantity,
                    (sum(m.qty) * m.weight) as total_weight,
                    ((sum(m.qty) * m.weight) * m.price_purchase) as mt_achat,
                    AVG(NULLIF(m.price_sale, 0)) as average_sale_price,
                    max(m.date) as write_date,
                    min(m.date) as create_date
                FROM
                    casa_stock_move m
                WHERE
                    m.state = 'done'
                GROUP BY
                    m.product_id, m.lot, m.dum, m.ville, m.frigo, m.ste_id, m.weight, m.price_purchase, m.calibre
                HAVING
                    sum(m.qty) != 0
            )
        """ % self._table)

    def action_new_exit(self):
        self.ensure_one()
        return {
            'name': 'Nouvelle Sortie',
            'type': 'ir.actions.act_window',
            'res_model': 'casa.stock.exit',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_product_id': self.product_id.id,
                'default_lot': self.lot,
                'default_dum': self.dum,
                'default_ville': self.ville,
                'default_frigo': self.frigo,
                'default_weight': self.weight,
                'default_calibre': self.calibre,
                'default_ste_id': self.ste_id.id, 
            }
        }
