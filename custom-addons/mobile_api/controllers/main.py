from odoo import http
from odoo.http import request

class MobileStockController(http.Controller):

    @http.route('/mobile/stock/snapshot', type='json', auth='user', methods=['GET', 'POST'])
    def get_stock_snapshot(self, **kwargs):
        """
        Returns a snapshot of the stock grouped by product, lot, dum, garage.
        Filters can be passed in kwargs:
        - product_id: int
        - garage: str
        """
        domain = []
        if kwargs.get('product_id'):
            domain.append(('product_id', '=', int(kwargs.get('product_id'))))
        if kwargs.get('garage'):
            domain.append(('garage', '=', kwargs.get('garage')))

        snapshot_recs = request.env['mobile.stock.snapshot'].search(domain)
        
        data = []
        for rec in snapshot_recs:
            data.append({
                'product_id': rec.product_id.id,
                'product_name': rec.product_name,
                'company_article_id': rec.company_article_id.id,
                'company_article_name': rec.company_article_id.name if rec.company_article_id else False,
                'garage': rec.garage,
                'lot': rec.lot,
                'dum': rec.dum,
                'quantity_available': rec.quantity_available,
                'entry_date': rec.entry_date,
                'weight': rec.weight,
                'calibre': rec.calibre,
            })
        
        return {'status': 'success', 'data': data}
