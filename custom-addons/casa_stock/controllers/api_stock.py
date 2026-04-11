import base64
import io
import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class ApiStockController(http.Controller):

    @http.route('/api/stock/consult', type='json', auth='public', methods=['POST'], csrf=False)
    def consult_stock(self, **kwargs):
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('api_stock.secret_key', 'n8n-secret-key-12345')
        
        if not api_key or api_key != expected_api_key:
            return {'status': 'error', 'message': 'Unauthorized'}

        try:
            data = request.jsonrequest if hasattr(request, 'jsonrequest') else kwargs
        except Exception:
            return {'status': 'error', 'message': 'Invalid JSON request'}

        product_name = data.get('product_name')
        if not product_name:
            return {'status': 'error', 'message': 'Missing product_name parameter'}

        article = request.env['company.article'].sudo().search([('name', 'ilike', product_name)], limit=1)
        if not article:
            return {'status': 'not_found', 'message': f"Article non trouvé pour '{product_name}'"}

        products = request.env['casa.product'].sudo().search([('article_id', '=', article.id)])
        if not products:
            return {'status': 'not_found', 'message': f"Aucun produit lié à l'article '{article.name}'"}

        stock_records = request.env['casa.stock.stock'].sudo().search([('product_id', 'in', products.ids)])
        
        total_general = sum(stock_records.mapped('total_weight'))
        if total_general <= 0:
            return {'status': 'not_found', 'message': f"Stock nul pour '{article.name}'"}

        par_ville = {}
        par_calibre = {}
        par_poids = {}

        for record in stock_records:
            ville = record.ville.capitalize() if record.ville else 'Inconnu'
            calibre = record.calibre or 'Inconnu'
            poids = record.poids or 'Inconnu'
            weight = record.total_weight or 0.0

            par_ville[ville] = par_ville.get(ville, 0.0) + weight
            par_calibre[calibre] = par_calibre.get(calibre, 0.0) + weight
            par_poids[poids] = par_poids.get(poids, 0.0) + weight

        # Arrondi
        for d in (par_ville, par_calibre, par_poids):
            for k in d:
                d[k] = round(d[k], 2)
        total_general = round(total_general, 2)

        excel_binary = ""
        if xlsxwriter:
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Etat de Stock')

            headers_excel = ['Produit', 'Lot', 'DUM', 'Ville', 'Calibre', 'Poids', 'Quantité', 'Tonnage']
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            
            for col_num, header in enumerate(headers_excel):
                worksheet.write(0, col_num, header, header_format)

            row = 1
            for rec in stock_records:
                # Exclude lines with 0 stock to avoid polluting excel
                if rec.quantity <= 0:
                    continue
                worksheet.write(row, 0, rec.product_id.name or '')
                worksheet.write(row, 1, rec.lot or '')
                worksheet.write(row, 2, rec.dum or '')
                worksheet.write(row, 3, rec.ville or '')
                worksheet.write(row, 4, rec.calibre or '')
                worksheet.write(row, 5, rec.poids or '')
                worksheet.write(row, 6, rec.quantity or 0.0)
                worksheet.write(row, 7, rec.total_weight or 0.0)
                row += 1

            workbook.close()
            output.seek(0)
            excel_binary = base64.b64encode(output.read()).decode('utf-8')
        
        return {
            "status": "success",
            "article_principal": article.name,
            "total_general": total_general,
            "details": {
                "par_ville": par_ville,
                "par_calibre": par_calibre,
                "par_poids": par_poids
            },
            "excel_binary": excel_binary,
            "file_name": f"Etat_Stock_{article.name.replace(' ', '_')}.xlsx"
        }
