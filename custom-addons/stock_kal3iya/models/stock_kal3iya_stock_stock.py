from odoo import models, fields, api, tools
from odoo.exceptions import UserError
from google.oauth2 import service_account
from googleapiclient.discovery import build

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
        ('frigo', 'Frigo'),
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

    def _compute_display_name(self):
        for record in self:
            parts = []
            if record.lot:
                parts.append(str(record.lot))
            if record.dum:
                parts.append(f"DUM: {record.dum}")
            if record.weight:
                parts.append(f"{record.weight}kg")
            if record.calibre:
                parts.append(f"Cal: {record.calibre}")
            
            record.display_name = " - ".join(parts) if parts else "N/A"

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
                    m.weight,
                    m.calibre,
                    sum(m.qty) as quantity,
                    max(m.price_purchase) as price,
                    sum(m.qty * m.price_purchase) as mt_achat,
                    max(m.date) as write_date,
                    min(m.date) as create_date
                FROM
                    stock_kal3iya_move m
                WHERE
                    m.state = 'done'
                GROUP BY
                    m.product_id, m.lot, m.dum, m.garage, m.ste_id, m.weight, m.calibre
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

    def action_new_transfer(self):
        self.ensure_one()
        return {
            'name': 'Nouveau Transfert',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.kal3iya.transfer',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_product_id': self.product_id.id,
                'default_lot': self.lot,
                'default_dum': self.dum,
                'default_garage_from': self.garage,
                'default_weight': self.weight,
                'default_calibre': self.calibre,
                'default_ste_id': self.ste_id.id,
                # Pre-fill source_line_id to ensure exact match logic in transfer onchange if needed
                # But transfer model logic relies on filtering. 
                # Passing defaults is enough for the user request "filled with all informations".
            }
        }

    
    def _get_drive_credentials_path(self):
        return "/srv/google_credentials/odoo_drive_service.json"

    def _get_drive_service(self):
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

        # 0. Check if we already have a link in the view (from underlying move)
        # However, the view field 'scan_dum' comes from max(move.scan_dum). 
        # If it's set, we can just open it. But the button condition usually relies on this.
        # If logic is "if scan_dum is empty, search drive", we proceed.
        
        if self.scan_dum:
             return {
                'type': 'ir.actions.act_url',
                'url': self.scan_dum,
                'target': 'new',
            }

        # 1. Connect to Drive
        service = self._get_drive_service()
        folder_id = '1i9kzO4Pk7X2hFJG2hyh828Sq5uAbarIA'
        
        # 2. Sanitize DUM (escape single quotes)
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

            # 6. Persist Linked to Moves (Critical Step)
            # Find all done moves with this DUM and Product (to be safe/specific)
            # We update even if they have a link (to refresh it) or only if empty? 
            # User said: "Store the webViewLink into the 'scan_dum' field... on the underlying stock.kal3iya.move records"
            domain = [
                ('dum', '=', self.dum),
                ('state', '=', 'done'),
                ('product_id', '=', self.product_id.id) # Scope to product as well to be safe
                # ('scan_dum', '=', False) # We can update all to ensure consistency
            ]
            moves = self.env['stock.kal3iya.move'].sudo().search(domain)
            if moves:
                moves.write({'scan_dum': file_url})

            return {
                'type': 'ir.actions.act_url',
                'url': file_url,
                'target': 'new',
            }
            
        except UserError:
            raise
        except Exception as e:
            raise UserError(f"Erreur lors de la recherche Drive: {str(e)}")

    @api.model
    def _cron_sync_dum_drive(self):
        """
        Scheduled Action to sync DUM PDFs from Drive to Move records.
        - Groups by DUM
        - One Drive call per DUM
        - Batch limit
        - Error handling per DUM
        """
        # 1. Find moves needing sync
        # We need DUMs where at least one move has no link.
        # To avoid complex group_by in search, we can just search for moves with no link and set DUM.
        domain = [
            ('state', '=', 'done'),
            ('dum', '!=', False),
            ('scan_dum', '=', False)
        ]
        # Limit search to avoid memory issues, we'll process distinct DUMs from this set
        # We fetch a bit more to ensure we get enough unique DUMs
        moves_to_sync = self.env['stock.kal3iya.move'].search(domain, limit=500)
        
        if not moves_to_sync:
            return

        # 2. Extract Unique DUMs (Set comprehension)
        unique_dums = list(set(m.dum for m in moves_to_sync))
        
        # 3. Apply Batch Limit for Drive Calls
        BATCH_LIMIT = 50
        dums_to_process = unique_dums[:BATCH_LIMIT]
        
        service = False
        try:
             service = self._get_drive_service()
        except Exception as e:
            # If we can't connect, fail the whole job
            raise e

        folder_id = '1i9kzO4Pk7X2hFJG2hyh828Sq5uAbarIA'

        for dum in dums_to_process:
            try:
                # Sanitize
                safe_dum = dum.replace("'", "\\'")
                
                # Query
                query = (
                    "mimeType='application/pdf' "
                    f"and name contains '{safe_dum}' "
                    f"and '{folder_id}' in parents "
                    "and trashed=false"
                )
                
                # Execute Drive Search
                results = service.files().list(
                    q=query,
                    fields="files(id, name, webViewLink, createdTime)",
                    orderBy="createdTime desc",
                    pageSize=1
                ).execute()
                
                files = results.get('files', [])
                
                if files:
                    file_url = files[0].get('webViewLink')
                    
                    # Update ALL moves with this DUM (globally for this DUM, not just the ones found in step 1)
                    # This ensures future consistency
                    sync_domain = [
                        ('dum', '=', dum),
                        ('state', '=', 'done')
                    ]
                    # We utilize sudo to ensure we can write to all valid records
                    moves_to_update = self.env['stock.kal3iya.move'].sudo().search(sync_domain)
                    moves_to_update.write({'scan_dum': file_url})
                    
                    # Log (optional, or rely on success)
                    # _logger.info(f"DUM Sync: Matched {dum} -> {file_url}")
            
            except Exception as e:
                # Log error but continue to next DUM
                # _logger.error(f"DUM Sync Error for {dum}: {str(e)}")
                continue
            
            # Commit is handled by Odoo at end of cron or we can manual commit if needed
            # For 50 items, standard behavior is fine.

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