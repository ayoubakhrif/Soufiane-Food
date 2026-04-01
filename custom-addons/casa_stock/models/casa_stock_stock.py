from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError

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
