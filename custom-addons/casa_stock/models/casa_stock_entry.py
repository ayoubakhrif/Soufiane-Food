from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re

class CasaStockEntry(models.Model):
    _name = 'casa.stock.entry'
    _description = 'Entrée Stock Casa'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence', readonly=True, default='/')
    product_id = fields.Many2one('casa.product', string='Produit', required=True, tracking=True)
    qty = fields.Float(string='Quantité', required=True, tracking=True)
    weight = fields.Float(string='Poids (Kg)', tracking=True)
    tonnage = fields.Float(string='Tonnage', compute='_compute_tonnage', store=True)
    
    price_purchase = fields.Float(string='Prix Achat', tracking=True)
    price_received = fields.Float(string='Prix reçu', tracking=True)
    mt_achat = fields.Float(
        string='Montant Achat',
        compute='_compute_amounts',
        store=True
    )
    
    @api.depends('tonnage', 'price_purchase')
    def _compute_amounts(self):
        for rec in self:
            rec.mt_achat = rec.tonnage * rec.price_purchase
    
    date = fields.Date(string='Date', required=True, tracking=True)
    lot = fields.Char(string='Lot', required=True, tracking=True)
    dum = fields.Char(string='DUM', required=True, tracking=True)
    calibre = fields.Char(string='Calibre', tracking=True)
    
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville', required=True, tracking=True)
    
    charge_transport = fields.Float(
        string='Charge transport',
        compute='_compute_charge_transport',
        store=True
    )
    
    provider_id = fields.Many2one('casa.provider', string='Fournisseur', tracking=True)
    driver_id = fields.Many2one('casa.driver', string='Chauffeur', tracking=True)
    ste_id = fields.Many2one('casa.ste', string='Société', tracking=True)
    image_1920 = fields.Image(related='product_id.image_1920', readonly=False)
    scan_dum = fields.Char(string='Scan DUM (Drive)', help="Poser le lien vers le scan de la DUM")
    stock_soufiane = fields.Boolean(string='Stock Soufiane', default=False, tracking=True)
    validation_user_id = fields.Many2one('res.users', string='Validé par', readonly=True, tracking=True)

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

            # 6. Save Link
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
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Validé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True, tracking=True)
    driver_phone = fields.Char(
        string='Téléphone chauffeur',
        related='driver_id.phone',
        readonly=True
    )
    poids = fields.Char(string='Poids', compute='_compute_poids')

    @api.depends('weight')
    def _compute_poids(self):
        for rec in self:
            rec.poids = f"{rec.weight or 0.0}Kg"

    move_id = fields.Many2one('casa.stock.move', string='Mouvement Stock', readonly=True)
    cancel_move_id = fields.Many2one('casa.stock.move', string='Mouvement d\'Annulation', readonly=True)
    is_cancel_hidden = fields.Boolean(compute='_compute_is_cancel_hidden')

    def _compute_is_cancel_hidden(self):
        is_manager = self.env.user.has_group('casa_stock.group_manager')
        hidden = not is_manager
        for rec in self:
            rec.is_cancel_hidden = hidden

    @api.depends('qty', 'weight')
    def _compute_tonnage(self):
        for rec in self:
            rec.tonnage = rec.qty * rec.weight

    @api.depends('tonnage', 'price_purchase')
    def _compute_amounts(self):
        for rec in self:
            rec.mt_achat = (rec.price_purchase or 0.0) * (rec.tonnage or 0.0)
    
    @api.depends('tonnage')
    def _compute_charge_transport(self):
        for rec in self:
            rec.charge_transport = (rec.tonnage or 0.0) * 0.02

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('casa.stock.entry') or '/'
        return super().create(vals)

    def write(self, vals):
        for rec in self:
            if rec.state in ('confirmed', 'done'):
                forbidden_fields = [
                    'product_id', 'qty', 'weight', 'price_purchase', 'price_received',
                    'date', 'lot', 'dum', 'ville', 'provider_id', 'driver_id', 'ste_id'
                ]
                if any(f in vals for f in forbidden_fields):
                    raise UserError(_("Les opérations confirmées ou validées ne peuvent pas être modifiées. Utilisez 'Annuler'."))
        return super().write(vals)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            rec.write({
                'state': 'confirmed',
            })

    def action_validate(self):
        for rec in self:
            if rec.state != 'confirmed':
                continue
            
            # Create Move
            move = self.env['casa.stock.move'].create({
                'product_id': rec.product_id.id,
                'lot': rec.lot,
                'dum': rec.dum,
                'ville': rec.ville,
                'qty': rec.qty,
                'move_type': 'entry',
                'state': 'done',
                'date': rec.date,
                'reference': rec.name,
                'price_purchase': rec.price_purchase,
                'price_received': rec.price_received,
                'weight': rec.weight,
                'calibre': rec.calibre,
                'scan_dum': rec.scan_dum,
                'stock_soufiane': rec.stock_soufiane,
                'provider_id': rec.provider_id.id,
                'driver_id': rec.driver_id.id,
                'ste_id': rec.ste_id.id,
                'res_model': 'casa.stock.entry',
                'res_id': rec.id,
            })
            rec.write({
                'state': 'done',
                'move_id': move.id,
                'validation_user_id': self.env.user.id
            })

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('confirmed', 'done'):
                raise UserError(_("Vous ne pouvez annuler que des entrées confirmées ou validées."))
            
            if rec.state == 'done':
                # Check if cancelling results in negative stock
                current_stock = self._get_current_stock_qty(rec)
                if current_stock < rec.qty:
                     raise UserError(_(
                        "Annulation impossible ! Le stock deviendrait négatif.\n"
                        "Stock actuel : %s, Quantité à retirer : %s.\n"
                        "Certaines quantités ont probablement déjà été vendues."
                    ) % (current_stock, rec.qty))

                # Create Reversal Move
                cancel_move = self.env['casa.stock.move'].create({
                    'product_id': rec.product_id.id,
                    'lot': rec.lot,
                    'dum': rec.dum,
                    'ville': rec.ville,
                    'qty': -rec.qty,
                    'move_type': 'cancel_entry',
                    'state': 'done',
                    'date': fields.Datetime.now(),
                    'reference': rec.name,
                    'price_purchase': rec.price_purchase,
                    'price_received': rec.price_received,
                    'weight': rec.weight,
                    'calibre': rec.calibre,
                    'stock_soufiane': rec.stock_soufiane,
                    'provider_id': rec.provider_id.id,
                    'driver_id': rec.driver_id.id,
                    'res_model': 'casa.stock.entry',
                    'res_id': rec.id,
                    'ste_id': rec.ste_id.id,
                })
                rec.write({
                    'state': 'cancel',
                    'cancel_move_id': cancel_move.id
                })
            elif rec.state == 'confirmed':
                rec.write({
                    'state': 'cancel'
                })

    def _get_current_stock_qty(self, rec, price=None):
        """Helper to get stock for specific dimensions."""
        domain = [
            ('product_id', '=', rec.product_id.id),
            ('ville', '=', rec.ville),
            ('ste_id', '=', rec.ste_id.id),
            ('state', '=', 'done')
        ]
        domain.append(('weight', '>=', (rec.weight or 0.0) - 0.01))
        domain.append(('weight', '<=', (rec.weight or 0.0) + 0.01))
        
        if rec.lot:
            domain.append(('lot', '=', rec.lot))
        else:
            domain.append(('lot', 'in', [False, '']))
            
        if rec.dum:
            domain.append(('dum', '=', rec.dum))
        else:
            domain.append(('dum', 'in', [False, '']))
            
        if rec.calibre:
            domain.append(('calibre', '=', rec.calibre))
        else:
            domain.append(('calibre', 'in', [False, '']))

        if price is not None:
             domain.append(('price_purchase', '>=', price - 0.01))
             domain.append(('price_purchase', '<=', price + 0.01))

        res = self.env['casa.stock.move'].read_group(domain, ['qty'], [])
        return res[0]['qty'] if res and res[0]['qty'] else 0.0

    @api.constrains('qty')
    def _check_qty_positive(self):
        for rec in self:
            if rec.qty <= 0:
                raise UserError(_("La quantité doit être strictement positive."))

    @api.constrains('weight', 'price_purchase')
    def _check_weight_price_positive(self):
        for rec in self:
            if rec.weight <= 0:
                raise ValidationError(_("Le poids doit être strictement positif."))
            if rec.price_purchase <= 0:
                raise ValidationError(_("Le prix d'achat doit être strictement positif."))

    @api.constrains('lot', 'dum')
    def _check_lot_dum_format(self):
        for rec in self:
            #LOT : doit contenir au moins un chiffre
            if rec.lot and not re.search(r'\d', rec.lot):
                raise ValidationError("LOT erroné.")
    
            # DUM : doit commencer par un chiffre
            if rec.dum and not re.match(r'^\d', rec.dum):
                raise ValidationError("DUM erroné.")