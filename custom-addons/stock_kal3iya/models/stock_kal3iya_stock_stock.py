from odoo import models, fields, api, tools

class StockKal3iyaStock(models.Model):
    _name = 'stock.kal3iya.stock'
    _description = 'Stock Kal3iya (Aggregation)'
    _auto = False
    _log_access = False
    _order = 'product_id'

    product_id = fields.Many2one('stock.kal3iya.product', string='Produit', readonly=True, required=True)
    lot = fields.Char(string='Lot', readonly=True, required=True)
    dum = fields.Char(string='DUM', readonly=True, required=True)
    scan_dum = fields.Char(string='Scan DUM', readonly=True)
    scan_invoice = fields.Char(string='Scan Facture', readonly=True)
    garage = fields.Selection([
        ('garage1', 'Garage 1'),
        ('garage2', 'Garage 2'),
        ('garage3', 'Garage 3'),
        ('garage4', 'Garage 4'),
        ('garage5', 'Garage 5'),
        ('garage6', 'Garage 6'),
        ('garage7', 'Garage 7'),
        ('garage8', 'Garage 8'),
        ('terrasse', 'Terrasse'),
        ('fenidek', 'Fenidek'),
    ], string='Garage')
    ste_id = fields.Many2one('stock.kal3iya.ste', string='Société', readonly=True)
    
    quantity = fields.Float(string='Quantité', readonly=True)
    weight = fields.Float(string='Poids (Kg)', readonly=True)
    calibre = fields.Char(string='Calibre', readonly=True)
    price = fields.Float(string='Dernier Prix (Achat)', readonly=True)
    mt_achat = fields.Float(string='Montant achat estimé', readonly=True)
    image_1920 = fields.Image(related='product_id.company_article_image', readonly=True)
    write_date = fields.Datetime(string='Last Update', readonly=True)
    create_date = fields.Datetime(string='Creation Date', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW stock_kal3iya_stock AS (
                SELECT
                    min(m.id) as id,
                    m.product_id,
                    m.lot,
                    m.dum,
                    max(m.scan_dum) as scan_dum,
                    max(m.scan_invoice) as scan_invoice,
                    m.garage,
                    m.ste_id,
                    sum(m.qty) as quantity,

                    max(CASE WHEN m.qty > 0 THEN m.weight END) as weight,
                    max(CASE WHEN m.qty > 0 THEN m.calibre END) as calibre,
                    max(CASE WHEN m.qty > 0 THEN m.price_purchase END) as price,

                    sum(m.qty * m.price_purchase) as mt_achat,
                    max(m.date) as write_date,
                    min(m.date) as create_date
                FROM
                    stock_kal3iya_move m
                WHERE
                    m.state = 'done'
                GROUP BY
                    m.product_id, m.lot, m.dum, m.garage, m.ste_id
                HAVING
                    sum(m.qty) != 0
            )
        """)

    def action_new_exit(self):
        self.ensure_one()
        return {
            'name': 'Nouvelle Sortie',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.kal3iya.exit',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_product_id': self.product_id.id,
                'default_lot': self.lot,
                'default_dum': self.dum,
                'default_garage': self.garage,
                'default_weight': self.weight,
                'default_calibre': self.calibre,
                'default_ste_id': self.ste_id.id, 
            }
        }

    def action_open_dum(self):
        self.ensure_one()
        if self.scan_dum:
            return {
                'type': 'ir.actions.act_url',
                'url': self.scan_dum,
                'target': 'new',
            }
        return False

    @api.model
    def validate_stock_exit(self, data):
        """
        Validate a stock exit request for AI Agent.
        
        Args:
            data (dict): {
                'product_name': str,
                'lot': str,
                'dum': str,
                'garage': str, # Selection key or label
                'qty': float,
                'ste_name': str (optional)
            }
            
        Returns:
            dict: {
                'valid': bool,
                'stock_found': bool,
                'available_qty': float,
                'errors': list[str],
                'normalized_data': dict (resolved IDs/Values)
            }
        """
        response = {
            'valid': False,
            'stock_found': False,
            'available_qty': 0.0,
            'errors': [],
            'normalized_data': {}
        }
        
        # 1. Normalize Inputs (Trim only, NO STRICT FORMATTING)
        raw_product = (data.get('product_name') or '').strip()
        raw_lot = (data.get('lot') or '').strip()
        raw_dum = (data.get('dum') or '').strip()
        raw_garage = (data.get('garage') or '').strip()
        qty = data.get('qty', 0.0)
        
        if not raw_product:
            response['errors'].append("Le nom du produit est requis.")
        if not raw_lot:
            response['errors'].append("Le numéro de LOT est requis.")
        if not raw_dum:
            response['errors'].append("Le numéro DUM est requis.")
        if not raw_garage:
            response['errors'].append("Le garage est requis.")
        if qty <= 0:
            response['errors'].append("La quantité doit être supérieure à 0.")
            
        if response['errors']:
            return response

        # 2. Resolve Product (Fuzzy / Alias)
        Product = self.env['stock.kal3iya.product']
        product = Product.search([('name', '=ilike', raw_product)], limit=1)
        
        if not product:
            # Try Alias
            alias = self.env['ai.alias'].search([
                ('model_name', '=', 'stock.kal3iya.product'),
                ('input_text', '=ilike', raw_product)
            ], limit=1)
            if alias:
                 product = Product.browse(alias.record_id)
        
        if not product:
            response['errors'].append(f"Produit non trouvé : '{raw_product}'")
            return response
            
        response['normalized_data']['product_id'] = product.id
        response['normalized_data']['product_name'] = product.name

        # 3. Resolve Garage (Selection)
        # We need to map text like "Garage 1" or "garage1" to the selection key "garage1"
        garage_key = False
        selection = self.fields_get(['garage'])['garage']['selection']
        
        # Direct key match
        for key, label in selection:
            if raw_garage.lower() == key.lower():
                garage_key = key
                break
        
        # Label match
        if not garage_key:
             for key, label in selection:
                if raw_garage.lower() == label.lower():
                    garage_key = key
                    break
        
        if not garage_key:
             response['errors'].append(f"Garage invalide : '{raw_garage}'")
             return response

        response['normalized_data']['garage'] = garage_key

        # 4. Check Stock Availability
        # Rely strictly on database content for LOT and DUM (Case Insensitive search is safer for user input)
        domain = [
            ('product_id', '=', product.id),
            ('garage', '=', garage_key),
            ('lot', '=ilike', raw_lot), 
            ('dum', '=ilike', raw_dum),
        ]
        
        stock_lines = self.search(domain)
        
        if not stock_lines:
            response['errors'].append("Aucun stock trouvé pour ces critères (Produit + Lot + DUM + Garage).")
            return response
            
        # 5. Calculate Total Available
        total_available = sum(line.quantity for line in stock_lines)
        response['stock_found'] = True
        response['available_qty'] = total_available
        
        # 6. Validate Quantity
        if qty > total_available:
            response['errors'].append(f"Stock insuffisant. Demandé: {qty}, Disponible: {total_available}")
            response['valid'] = False
        else:
            response['valid'] = True
            
        # Pass back the exact LOT/DUM found (or the input if multiple/fuzzy match, but here we used ilike)
        # Ideally we return the one from the database to standardize subsequent calls
        response['normalized_data']['lot'] = stock_lines[0].lot 
        response['normalized_data']['dum'] = stock_lines[0].dum
        
        return response

    def action_open_invoice(self):
        self.ensure_one()
        if self.scan_invoice:
            return {
                'type': 'ir.actions.act_url',
                'url': self.scan_invoice,
                'target': 'new',
            }
        return False