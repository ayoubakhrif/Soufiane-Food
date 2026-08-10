from odoo import models, fields, api, _
from odoo.exceptions import UserError
from google.oauth2 import service_account
from googleapiclient.discovery import build

class StockKal3iyaEntry(models.Model):
    _name = 'stock.kal3iya.entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Entrée Stock Kal3iya'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', readonly=True, default='/')
    product_id = fields.Many2one('stock.kal3iya.product', string='Produit')
    company_article_id = fields.Many2one('company.article', string='Article Société', related='product_id.company_article_id', store=True)
    qty = fields.Float(string='Quantité', required=True)
    weight = fields.Float(string='Poids (Kg)')
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)
    
    price_purchase = fields.Float(string='Prix Achat')
    
    date = fields.Date(string='Date')
    lot = fields.Char(string='Lot')
    dum = fields.Char(string='DUM')
    calibre = fields.Char(string='Calibre')
    
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
    
    provider_id = fields.Many2one('stock.kal3iya.provider', string='Fournisseur')
    driver_id = fields.Many2one('stock.kal3iya.driver', string='Chauffeur')
    ste_id = fields.Many2one('stock.kal3iya.ste', string='Société')
    image_1920 = fields.Image(related='product_id.company_article_image', readonly=False)
    scan_dum = fields.Char(string='Scan DUM (Drive)', help="Poser le lien vers le scan de la DUM")
    scan_invoice = fields.Char(string='Scan Facture (Drive)', help="Poser le lien vers le scan de la Facture")
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Confirmé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True)

    move_id = fields.Many2one('stock.kal3iya.move', string='Mouvement Stock', readonly=True)
    cancel_move_id = fields.Many2one('stock.kal3iya.move', string='Mouvement d\'Annulation', readonly=True)

    @api.depends('qty', 'weight')
    def _compute_tonnage(self):
        for rec in self:
            rec.tonnage = rec.qty * rec.weight

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.kal3iya.entry') or '/'
        return super(StockKal3iyaEntry, self).create(vals)

    def write(self, vals):
        for rec in self:
            if rec.state == 'done':
                forbidden_fields = [
                    'product_id', 'qty', 'weight', 'price_purchase',
                    'date', 'lot', 'dum', 'garage', 'provider_id', 'driver_id', 'ste_id'
                ]
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Les opérations confirmées ne peuvent pas être modifiées. Utilisez 'Annuler' et créez une nouvelle opération."))
        return super(StockKal3iyaEntry, self).write(vals)

    def _get_drive_credentials_path(self):
        return "/srv/google_credentials/service_account.json"

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

            # 6. Save Link to THIS entry only
            self.write({'scan_dum': file_url})

            return {
                'type': 'ir.actions.act_url',
                'url': file_url,
                'target': 'new',
            }
            
        except UserError:
            raise
        except Exception as e:
            raise UserError(f"Erreur lors de la recherche Drive: {str(e)}")

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            
            # Create Move
            move = self.env['stock.kal3iya.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'scan_dum': rec.scan_dum,
                'scan_invoice': rec.scan_invoice,
                'garage': rec.garage,
                'qty': rec.qty,
                'move_type': 'entry',
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,
                'price_purchase': rec.price_purchase,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'provider_id': rec.provider_id.id,
                'driver_id': rec.driver_id.id,
                'ste_id': rec.ste_id.id,
                'res_model': 'stock.kal3iya.entry',
                'res_id': rec.id,
            })
            rec.write({
                'state': 'done',
                'move_id': move.id
            })

    def action_cancel(self):
        for rec in self:
            if rec.state != 'done':
                raise UserError(_("Vous ne pouvez annuler que des entrées confirmées."))
            
            # Create Reversal Move
            cancel_move = self.env['stock.kal3iya.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'garage': rec.garage,
                'qty': -rec.qty,
                'move_type': 'cancel_entry',
                'state': 'done',
                'date': fields.Datetime.now(),
                'reference': rec.name,
                'price_purchase': rec.price_purchase,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'provider_id': rec.provider_id.id,
                'driver_id': rec.driver_id.id,
                'res_model': 'stock.kal3iya.entry',
                'res_id': rec.id,
                'ste_id': rec.ste_id.id,
            })
            rec.write({
                'state': 'cancel',
                'cancel_move_id': cancel_move.id
            })

    #@api.constrains('qty')
    #def _check_qty_positive(self):
     #   for rec in self:
      #      if rec.qty <= 0:
       #         raise UserError(_("La quantité doit être strictement positive."))



