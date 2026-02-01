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

    def action_open_invoice(self):
        self.ensure_one()
        if self.scan_invoice:
            return {
                'type': 'ir.actions.act_url',
                'url': self.scan_invoice,
                'target': 'new',
            }
        return False

    @api.model
    def validate_stock_exit(self, data):
        """
        Validate a stock exit request for AI Agent with Progressive Checks.
        """
        response = {
            'valid': False,
            'stock_found': False,
            'available_qty': 0.0,
            'errors': [],
            'normalized_data': {}
        }
        
        # 1. Normalize Inputs
        raw_product = (data.get('product_name') or '').strip()
        raw_lot = (data.get('lot') or '').strip()
        raw_dum = (data.get('dum') or '').strip() # Optional
        raw_garage = (data.get('garage') or '').strip() # Optional
        qty = float(data.get('qty', 0.0))
        
        if not raw_product:
            response['errors'].append("Produit requis")
        if not raw_lot:
            response['errors'].append("Lot requis")
        if qty <= 0:
            response['errors'].append("Quantité invalide")
            
        if response['errors']:
            return response

        # 2. Resolve Product
        Product = self.env['stock.kal3iya.product']
        product = Product.search([('name', '=ilike', raw_product)], limit=1)
        
        if not product:
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
        
        # 3. Progressive Validation
        
        # A. Check Lot Existence
        domain_lot = [('product_id', '=', product.id), ('lot', '=ilike', raw_lot)]
        if not self.search_count(domain_lot):
             response['errors'].append("Lot non trouvé pour ce produit")
             return response

        # B. Check DUM (if provided)
        if raw_dum:
            domain_dum = domain_lot + [('dum', '=ilike', raw_dum)]
            if not self.search_count(domain_dum):
                 # Try to be helpful: does the DUM exist at all for this product?
                 # If yes, mismatch logic. If no, DUM logic. 
                 # User wanted simple: "DUM non trouvé pour ce produit/lot"
                 response['errors'].append("DUM non trouvé pour ce produit/lot")
                 return response
                 
        # C. Check Garage (if provided)
        garage_key = False
        if raw_garage:
            selection = self.fields_get(['garage'])['garage']['selection']
            found = False
            for key, label in selection:
                if raw_garage.lower() == key.lower() or raw_garage.lower() == label.lower():
                    garage_key = key
                    found = True
                    break
            
            if not found:
                 response['errors'].append(f"Garage invalide (inconnu): {raw_garage}")
                 return response
                 
            # Check stock in this garage
            current_base_domain = domain_dum if raw_dum else domain_lot
            domain_garage = current_base_domain + [('garage', '=', garage_key)]
            
            if not self.search_count(domain_garage):
                 response['errors'].append("Garage non trouvé pour ce produit/lot")
                 return response

        # 4. Final Aggregation (at this point, we know lines exist)
        final_domain = [('product_id', '=', product.id), ('lot', '=ilike', raw_lot)]
        if raw_dum: final_domain.append(('dum', '=ilike', raw_dum))
        if garage_key: final_domain.append(('garage', '=', garage_key))
        
        stock_lines = self.search(final_domain)
        
        total_available = sum(line.quantity for line in stock_lines)
        response['available_qty'] = total_available
        response['stock_found'] = True
        
        # Populate Normalized Data with EXACT DB values from the first line found
        first_line = stock_lines[0]
        response['normalized_data']['lot'] = first_line.lot
        if raw_dum:
             response['normalized_data']['dum'] = first_line.dum
        if garage_key:
             response['normalized_data']['garage'] = first_line.garage
        
        response['normalized_data']['matched_lines'] = len(stock_lines)
        
        # 5. Quantity Check
        if qty > total_available:
            response['errors'].append(f"Stock insuffisant (Requis: {qty}, Dispo: {total_available})")
            response['valid'] = False
        else:
            response['valid'] = True
            
        return response