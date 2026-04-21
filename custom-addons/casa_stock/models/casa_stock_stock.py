from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
import base64
import io
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class CasaStockStock(models.Model):
    _name = 'casa.stock.stock'
    _description = 'Stock Casa (Aggregation)'
    _auto = False
    _log_access = False
    _order = 'quantity desc, product_id'

    product_id = fields.Many2one('casa.product', string='Produit', readonly=True)
    lot = fields.Char(string='Lot', readonly=True)
    dum = fields.Char(string='DUM', readonly=True)
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville', readonly=True)
    ste_id = fields.Many2one('casa.ste', string='Société', readonly=True)
    
    quantity = fields.Float(string='Quantité', readonly=True)
    weight = fields.Float(string='Poids (Kg)', readonly=True)
    poids = fields.Char(string='Poids', readonly=True)
    calibre = fields.Char(string='Calibre', readonly=True)
    price = fields.Float(string='Dernier Prix (Achat)', readonly=True)
    mt_achat = fields.Float(string='Montant achat estimé', readonly=True)
    average_sale_price = fields.Float(string='P.V. Moyen', readonly=True)
    image_1920 = fields.Image(related='product_id.image_1920', readonly=True)
    write_date = fields.Datetime(string='Last Update', readonly=True)
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    scan_dum = fields.Char(string='Scan DUM (Drive)', readonly=True)
    stock_soufiane = fields.Boolean(string='Stock Soufiane', readonly=True)

    total_weight = fields.Float(string='Tonnage', readonly=True)

    def _get_drive_credentials_path(self):
        return "/srv/google_credentials/service_account.json"

    def _get_drive_service(self):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds_path = self._get_drive_credentials_path()
        try:
            scopes = ['https://www.googleapis.com/auth/drive.readonly']
            creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            raise UserError(f"Erreur de connexion Google Drive: {str(e)}")

    def action_open_dum(self):
        self.ensure_one()
        if not self.dum:
            return False

        if self.scan_dum:
             return {
                'type': 'ir.actions.act_url',
                'url': self.scan_dum,
                'target': 'new',
            }

        # 1. Connect to Drive
        service = self._get_drive_service()
        folder_id = '1i9kzO4Pk7X2hFJG2hyh828Sq5uAbarIA'
        
        # 2. Sanitize DUM
        safe_dum = self.dum.replace("'", "\\'")
        
        # 3. Build Query
        query = (
            "mimeType='application/pdf' "
            f"and name contains '{safe_dum}' "
            f"and '{folder_id}' in parents "
            "and trashed=false"
        )
        
        try:
            # 4. Execute Search
            results = service.files().list(
                q=query,
                fields="files(id, name, webViewLink, createdTime)",
                orderBy="createdTime desc",
                pageSize=1
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                raise UserError(f"Aucun fichier PDF trouvé pour le DUM '{self.dum}' dans le dossier spécifié.")
                
            # 5. Get Link
            file_url = files[0].get('webViewLink')

            # 6. Update entries and moves related to this DUM to save the link
            # Since casa.stock.stock is an aggregation, we update all moves with this DUM
            moves = self.env['casa.stock.move'].search([('dum', '=', self.dum)])
            moves.write({'scan_dum': file_url})
            
            # Also find entries
            entries = self.env['casa.stock.entry'].search([('dum', '=', self.dum)])
            entries.write({'scan_dum': file_url})

            return {
                'type': 'ir.actions.act_url',
                'url': file_url,
                'target': 'new',
            }
        except UserError:
            raise
        except Exception as e:
            raise UserError(f"Erreur lors de la recherche Drive: {str(e)}")

    @api.depends('product_id.name', 'lot', 'dum', 'price', 'create_date')
    def _compute_display_name(self):
        for rec in self:
            name_parts = [rec.product_id.name] if rec.product_id else ['Inconnu']
            if rec.lot:
                name_parts.append(f"Lot: {rec.lot}")
            if rec.dum:
                name_parts.append(f"DUM: {rec.dum}")
            if rec.price:
                name_parts.append(f"{rec.price} MAD")
            
            # Show availability in name
            qty_str = f"{rec.quantity} ({rec.total_weight:.2f}T)"
            name_parts.append(f"Dispo: {qty_str}")
            
            if rec.create_date:
                name_parts.append(rec.create_date.strftime('%Y-%m-%d'))
                
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
                    max(m.ste_id) as ste_id,
                    m.calibre,
                    m.weight,
                    m.weight || 'Kg' as poids,
                    m.price_purchase as price,
                    bool_or(m.stock_soufiane) as stock_soufiane,
                    sum(m.qty) as quantity,
                    (sum(m.qty) * m.weight) as total_weight,
                    ((sum(m.qty) * m.weight) * m.price_purchase) as mt_achat,
                    AVG(NULLIF(m.price_sale, 0)) as average_sale_price,
                    max(m.date) as write_date,
                    min(m.date) as create_date,
                    min(m.date) as date,
                    max(m.scan_dum) as scan_dum
                FROM
                    casa_stock_move m
                WHERE
                    m.state = 'done'
                GROUP BY
                    m.product_id, m.lot, m.dum, m.ville, m.weight, m.price_purchase, m.calibre
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
                'default_weight': self.weight,
                'default_calibre': self.calibre,
                'default_ste_id': self.ste_id.id, 
                'default_price_purchase': self.price,
                'default_stock_soufiane': self.stock_soufiane,
                'default_is_from_stock': True,
            }
        }

    def action_new_perte(self):
        self.ensure_one()
        return {
            'name': _('Déclarer une Perte'),
            'type': 'ir.actions.act_window',
            'res_model': 'casa.stock.perte',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_stock_id': self.id,
                'default_product_id': self.product_id.id,
                'default_lot': self.lot,
                'default_dum': self.dum,
                'default_ville': self.ville,
                'default_weight': self.weight,
                'default_calibre': self.calibre,
                'default_ste_id': self.ste_id.id, 
                'default_price_purchase': self.price,
                'default_stock_soufiane': self.stock_soufiane,
            }
        }
    def action_export_stock_excel(self):
        # If called from a list view with selection, use selected records.
        # Otherwise, export all stock with quantity != 0
        records = self if self else self.search([('quantity', '!=', 0)])
        
        if not xlsxwriter:
            raise ValidationError("La bibliothèque xlsxwriter n'est pas installée.")

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Styles
        title_style = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'bg_color': '#D7E4BC', 'border': 1})
        header_style = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#f2f2f2'})
        cell_style = workbook.add_format({'border': 1})
        date_style = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})
        money_style = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        float_style = workbook.add_format({'border': 1, 'num_format': '#,##0.000'})

        sheet = workbook.add_worksheet("Stock Casa")
        
        # Headers
        headers = [
            "Date", "Produit", "Lot", "DUM", "Ville", 
            "Quantité", "Poids (Kg)", "Tonnage (T)", "Prix Achat", "Mt Achat"
        ]
        
        # Set column widths
        sheet.set_column(0, 0, 12)  # Date
        sheet.set_column(1, 1, 35)  # Produit
        sheet.set_column(2, 3, 15)  # Lot, DUM
        sheet.set_column(4, 4, 12)  # Ville
        sheet.set_column(5, 7, 12)  # Qty, Poids, Tonnage
        sheet.set_column(8, 9, 15)  # Prix, Mt Achat

        # Title
        sheet.merge_range('A1:J1', f"État du Stock Casa - {fields.Date.today()}", title_style)
        
        # Write Headers
        for col, header in enumerate(headers):
            sheet.write(2, col, header, header_style)
            
        row = 3
        for rec in records:
            # Date
            if rec.date:
                from datetime import datetime, time
                d = datetime.combine(rec.date, time.min)
                sheet.write_datetime(row, 0, d, date_style)
            else:
                sheet.write(row, 0, "", cell_style)
                
            sheet.write(row, 1, rec.product_id.name or "", cell_style)
            sheet.write(row, 2, rec.lot or "", cell_style)
            sheet.write(row, 3, rec.dum or "", cell_style)
            sheet.write(row, 4, dict(self._fields['ville'].selection).get(rec.ville, "") if rec.ville else "", cell_style)
            
            sheet.write_number(row, 5, rec.quantity or 0.0, float_style)
            sheet.write_number(row, 6, rec.weight or 0.0, float_style)
            sheet.write_number(row, 7, rec.total_weight or 0.0, float_style)
            sheet.write_number(row, 8, rec.price or 0.0, money_style)
            sheet.write_number(row, 9, rec.mt_achat or 0.0, money_style)
            
            row += 1
            
        # Add totals
        sheet.write(row, 4, "TOTAL", header_style)
        sheet.write_formula(row, 5, f'=SUM(F4:F{row})', float_style)
        sheet.write_formula(row, 7, f'=SUM(H4:H{row})', float_style)
        sheet.write_formula(row, 9, f'=SUM(J4:J{row})', money_style)

        row += 2
        
        # Gestia Branding
        sheet.write(row, 0, "This file is generated by Gestia ERP", workbook.add_format({'italic': True, 'font_size': 10}))
        

        workbook.close()
        output.seek(0)
        
        file_data = base64.b64encode(output.read())
        output.close()
        
        filename = f"Stock_Casa_{fields.Date.today()}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': file_data,
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_export_product_report_excel(self):
        if not self:
            raise UserError(_("Veuillez sélectionner au moins un enregistrement."))
            
        product = self[0].product_id
        if any(rec.product_id != product for rec in self):
            raise UserError(_("Tous les enregistrements sélectionnés doivent appartenir au même produit."))

        if not xlsxwriter:
            raise ValidationError("La bibliothèque xlsxwriter n'est pas installée.")

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Styles
        header_base = {'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 20}
        yellow_style = workbook.add_format({**header_base, 'bg_color': '#FCE9DA'})
        pink_style = workbook.add_format({**header_base, 'bg_color': '#FF00FF'})
        
        table_header_style = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#FCE9DA', 'font_size': 12})
        
        blue_style = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#6DA9DC', 'font_size': 12})
        orange_style = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#FF9900', 'font_size': 12, 'num_format': '#,##0'})
        
        cell_style = workbook.add_format({'border': 1, 'align': 'center', 'font_size': 12})
        money_style = workbook.add_format({'border': 1, 'align': 'center', 'font_size': 12, 'num_format': '#,##0.00'})
        float_style = workbook.add_format({'border': 1, 'align': 'center', 'font_size': 12, 'num_format': '#,##0.0'})
        
        cyan_style = workbook.add_format({'bold': True, 'border': 1, 'align': 'right', 'bg_color': '#00FFFF', 'font_size': 14, 'num_format': '#,##0.00'})

        sheet = workbook.add_worksheet("Rapport Produit")
        
        # Column setup
        sheet.set_column(0, 0, 25) # Qualibre
        sheet.set_column(1, 1, 15) # Qté global
        sheet.set_column(2, 2, 10) # Poids
        sheet.set_column(3, 3, 15) # Tonnage
        sheet.set_column(4, 4, 15) # Prix
        sheet.set_column(5, 5, 20) # Total

        # Header Row
        row = 1
        today_str = fields.Date.today().strftime('%d/%m/%y')
        sheet.write(row, 0, today_str, yellow_style)
        sheet.merge_range(row, 1, row, 4, product.name, pink_style)
        
        row += 2
        
        # Group records by city
        cities = ['tanger', 'casa']
        records_by_city = {city: self.filtered(lambda r: r.ville == city) for city in cities}
        
        for city_code in cities:
            records = records_by_city[city_code]
            if not records:
                continue
                
            # City Header
            city_label = dict(self._fields['ville'].selection).get(city_code, city_code).upper()
            sheet.merge_range(row, 0, row, 5, city_label, yellow_style)
            row += 1
            
            # Table Headers
            headers = ["Qualibre", "Qté global", "Poids", "Tonnage", "Prix", "Total"]
            sheet.write_row(row, 0, headers, table_header_style)
            row += 1
            
            # Aggregate data for this city
            aggregated = {}
            for rec in records:
                key = (rec.calibre or "", rec.weight or 0.0, rec.price or 0.0)
                if key not in aggregated:
                    aggregated[key] = {'qty': 0, 'tonnage': 0, 'total': 0}
                aggregated[key]['qty'] += rec.quantity
                aggregated[key]['tonnage'] += rec.total_weight
                aggregated[key]['total'] += rec.mt_achat
                
            city_qty_total = 0
            city_tonnage_total = 0
            city_mt_total = 0
            
            for (calibre, weight, price), data in aggregated.items():
                sheet.write(row, 0, calibre or "", blue_style)
                sheet.write_number(row, 1, data['qty'], orange_style)
                sheet.write_number(row, 2, weight, cell_style)
                sheet.write_number(row, 3, data['tonnage'], float_style)
                sheet.write_number(row, 4, price, money_style)
                sheet.write_number(row, 5, data['total'], money_style)
                
                city_qty_total += data['qty']
                city_tonnage_total += data['tonnage']
                city_mt_total += data['total']
                row += 1
                
            # City Totals
            sheet.write(row, 0, "TOTAL " + city_label, blue_style)
            sheet.write_number(row, 1, city_qty_total, orange_style)
            sheet.write(row, 2, "", cell_style)
            sheet.write_number(row, 3, city_tonnage_total, float_style)
            sheet.write(row, 4, "", cell_style)
            sheet.write_number(row, 5, city_mt_total, cyan_style)
            
            row += 2 # Space between tables

        row += 1
        
        # Gestia Branding
        sheet.write(row, 0, "This file is generated by Gestia ERP", workbook.add_format({'italic': True, 'font_size': 10}))
        

        workbook.close()
        output.seek(0)
        
        file_data = base64.b64encode(output.read())
        output.close()
        
        filename = f"Stock_Casa_{fields.Date.today()}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': file_data,
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def _get_product_report_data(self):
        """Prepare data for the QWeb PDF report, mimicking the Excel aggregation."""
        if not self:
            return {'cities': []}
            
        product = self[0].product_id
        cities_selection = dict(self._fields['ville'].selection)
        cities_to_process = ['tanger', 'casa']
        
        records_by_city = {city: self.filtered(lambda r: r.ville == city) for city in cities_to_process}
        
        report_data = {
            'product_name': product.name,
            'cities': []
        }
        
        for city_code in cities_to_process:
            records = records_by_city[city_code]
            if not records:
                continue
                
            city_label = cities_selection.get(city_code, city_code).upper()
            
            # Aggregate data for this city
            aggregated = {}
            for rec in records:
                key = (rec.product_id.name, rec.calibre or "", rec.weight or 0.0, rec.price or 0.0)
                if key not in aggregated:
                    aggregated[key] = {'qty': 0, 'tonnage': 0, 'total': 0}
                aggregated[key]['qty'] += rec.quantity
                aggregated[key]['tonnage'] += rec.total_weight
                aggregated[key]['total'] += rec.mt_achat
                
            lines = []
            city_qty_total = 0
            city_tonnage_total = 0
            city_mt_total = 0
            
            for (prod_name, calibre, weight, price), data in aggregated.items():
                display_calibre = f"{prod_name} - {calibre}" if calibre else prod_name
                lines.append({
                    'calibre': display_calibre,
                    'qty': data['qty'],
                    'weight': weight,
                    'tonnage': data['tonnage'],
                    'price': price,
                    'total': data['total']
                })
                city_qty_total += data['qty']
                city_tonnage_total += data['tonnage']
                city_mt_total += data['total']
                
            report_data['cities'].append({
                'name': city_label,
                'lines': lines,
                'total_qty': city_qty_total,
                'total_tonnage': city_tonnage_total,
                'total_amount': city_mt_total
            })
            
        return report_data

    def action_export_product_report_pdf(self):
        """Trigger the PDF report."""
        if not self:
            raise UserError(_("Veuillez sélectionner au moins un enregistrement."))
            
        product = self[0].product_id
        if any(rec.product_id != product for rec in self):
            raise UserError(_("Tous les enregistrements sélectionnés doivent appartenir au même produit."))
            
        return self.env.ref('casa_stock.action_report_casa_stock_product').report_action(self)

    def _get_general_report_data(self):
        """Prepare data for the Global Stock Summary report."""
        # Find all stock entries with positive quantity
        all_stock = self.search([('quantity', '>', 0)])
        if not all_stock:
            return {'cities': []}

        cities_selection = dict(self._fields['ville'].selection)
        cities_to_process = ['tanger', 'casa']
        
        report_data = {
            'report_date': fields.Date.today().strftime('%d/%m/%y'),
            'cities': []
        }
        
        total_global_tonnage = 0
        total_global_amount = 0

        for city_code in cities_to_process:
            city_records = all_stock.filtered(lambda r: r.ville == city_code)
            if not city_records:
                continue
                
            city_label = cities_selection.get(city_code, city_code).upper()
            
            # Aggregate by product name
            aggregated = {}
            for rec in city_records:
                prod_name = rec.product_id.name
                if prod_name not in aggregated:
                    aggregated[prod_name] = {'qty': 0, 'tonnage': 0, 'total': 0}
                aggregated[prod_name]['qty'] += rec.quantity
                aggregated[prod_name]['tonnage'] += rec.total_weight
                aggregated[prod_name]['total'] += rec.mt_achat
                
            lines = []
            city_qty_total = 0
            city_tonnage_total = 0
            city_mt_total = 0
            
            # Sort products alphabetically
            sorted_products = sorted(aggregated.keys())
            
            for prod_name in sorted_products:
                data = aggregated[prod_name]
                lines.append({
                    'product': prod_name,
                    'qty': data['qty'],
                    'tonnage': data['tonnage'],
                    'total': data['total']
                })
                city_qty_total += data['qty']
                city_tonnage_total += data['tonnage']
                city_mt_total += data['total']
                
            report_data['cities'].append({
                'name': city_label,
                'lines': lines,
                'total_qty': city_qty_total,
                'total_tonnage': city_tonnage_total,
                'total_amount': city_mt_total
            })
            
            total_global_tonnage += city_tonnage_total
            total_global_amount += city_mt_total

        report_data['global_tonnage'] = total_global_tonnage
        report_data['global_amount'] = total_global_amount
            
        return report_data

    def action_export_general_report_pdf(self):
        """Trigger the Global Stock Summary PDF report."""
        return self.env.ref('casa_stock.action_report_casa_stock_general').report_action(self)
