from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta
import base64
import io
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class LogisticsEntry(models.Model):
    _inherit = 'logistique.entry'

    contract_id = fields.Many2one('achat.contract', string='Contract', domain="[('state', '=', 'open')]")
    free_time_negotiated = fields.Integer(string='Negotiated Free Time')

    is_non_change = fields.Boolean(string='Non Changé', default=False,
                                   help='Cocher si le dossier n\'a pas encore été changé')

    date_booking = fields.Date(string='Date of Booking')
    date_docs_received = fields.Date(string='Date Documents Received')
    date_docs_confirmed = fields.Date(string='Date Documents Confirmed')

    origin_id = fields.Many2one(
        'achat.origin',
        string='Origin'
    )

    
    # Document Link
    document_ids = fields.One2many('logistique.entry.document', 'entry_id', string='Documents')

    display_name = fields.Char(compute='_compute_display_name') # Just to ensure we have it if needed

    eta_this_week = fields.Boolean(
        string='ETA cette semaine',
        compute='_compute_eta_this_week',
        store=True,
        help='True if ETA <= next Thursday (inclusive) and port_status is on_port',
    )

    @api.depends('eta', 'port_status')
    def _compute_eta_this_week(self):
        today = date.today()
        days_to_thursday = (3 - today.weekday()) % 7
        next_thursday = today + timedelta(days=days_to_thursday)
        for rec in self:
            rec.eta_this_week = (
                rec.port_status == 'on_port'
                and bool(rec.eta)
                and rec.eta <= next_thursday
            )

    calendar_label = fields.Char(string='Label Calendrier', compute='_compute_calendar_label')

    @api.depends('supplier_id.name', 'achat_article_id.name', 'ste_id.name', 'amount_total')
    def _compute_calendar_label(self):
        for rec in self:
            supplier = rec.supplier_id.name or ''
            article = rec.achat_article_id.name or ''
            ste = rec.ste_id.name or ''
            total = rec.amount_total or 0.0
            # Format total with space as thousands separator
            total_str = "{:,.2f}".format(total).replace(",", " ")
            rec.calendar_label = f"{supplier} - {article} - {ste} - {total_str} USD"

    @api.depends('calendar_label', 'bl_number')
    def _compute_display_name(self):
        for rec in self:
            if self.env.context.get('show_bl_number'):
                rec.display_name = rec.bl_number or "Nouveau"
            elif rec.calendar_label:
                rec.display_name = rec.calendar_label
            else:
                rec.display_name = rec.bl_number or "Nouveau"

    @api.constrains('bl_number', 'contract_id')
    def _check_bl_contract_unique(self):
        """Prevent duplicate BL numbers for the same contract"""
        for rec in self:
            if rec.bl_number and rec.contract_id:
                duplicate = self.search([
                    ('id', '!=', rec.id),
                    ('bl_number', '=', rec.bl_number),
                    ('contract_id', '=', rec.contract_id.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f"The BL '{rec.bl_number}' exists already for this contract '{rec.contract_id.name}'.\n"
                        f"The same BL number cannot be used twice for the same contract."
                    )

    @api.constrains('price_unit')
    def _check_price_unit(self):
        for rec in self:
            if rec.price_unit <= 0:
                raise ValidationError("Le prix unitaire (P.U) doit être strictement supérieur à 0.")

    def action_confirm_purchase(self):
        # FIX: Allow regular purchase users to confirm too
        if not self.env.user.has_group('achat.group_purchase_user'):
            raise ValidationError("Only Purchase Users/Managers can confirm a dossier.")
        self.write({'purchase_state': 'confirmed'})

    def action_reset_to_initial(self):
        """Admin-only: Reset purchase state back to Initial."""
        self.write({'purchase_state': 'initial'})

    def action_reset_to_draft(self):
        """Admin-only: Reset purchase state back to Draft."""
        self.write({'purchase_state': 'draft'})

    legacy_article_id = fields.Many2one('logistique.article', string='Article (Ancien)', readonly=True)
    achat_article_id = fields.Many2one('achat.article', string='Article')
    details = fields.Char(string='Details')

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        if self.contract_id:
            self.contract_num = self.contract_id.name
            self.supplier_id = self.contract_id.supplier_id
            self.ste_id = self.contract_id.ste_id
            self.achat_article_id = self.contract_id.article_id
            self.incoterm = self.contract_id.incoterm
            self.details = self.contract_id.details

            self.origin_id = self.contract_id.origin_id
            self.free_time_negotiated = self.contract_id.free_time_negotiated
            # Pre-fill actual free time with negotiated value
            self.free_time = self.contract_id.free_time_negotiated
            if self.contract_id.weight_total:
                self.weight = self.contract_id.weight_total # Optional sync, user might update per shipment

    def action_generate_excel_dossiers_to_exit(self):
        if not xlsxwriter:
            raise ValidationError("La bibliothèque xlsxwriter n'est pas installée.")

        from datetime import datetime, time
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # --- DÉFINITION DES STYLES ---
        header_style = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#C6E0B4', 'font_size': 10, 'text_wrap': True
        })
        
        cell_style = workbook.add_format({'border': 1, 'valign': 'vcenter', 'font_size': 9})
        
        date_style = workbook.add_format({
            'border': 1, 'num_format': 'dd/mm/yyyy', 'align': 'center', 'font_size': 9
        })
        
        num_style = workbook.add_format({
            'border': 1, 'num_format': '#,##0.00', 'align': 'right', 'font_size': 9
        })

        total_row_style = workbook.add_format({
            'bold': True, 'border': 1, 'bg_color': '#D9D9D9', 'num_format': '#,##0.00', 'font_size': 10
        })

        sheet = workbook.add_worksheet("SUIVI WEEK")

        # Configuration des colonnes selon votre modèle
        sheet.set_column('A:A', 18)  # Importer
        sheet.set_column('B:B', 25)  # Exporter
        sheet.set_column('C:C', 6)   # FCL (Conteneurs count)
        sheet.set_column('D:D', 18)  # INV / CONTRACT
        sheet.set_column('E:E', 15)  # PRODUCT
        sheet.set_column('F:F', 20)  # DETAILS
        sheet.set_column('G:I', 12)  # Weight, UP, Total
        sheet.set_column('J:K', 10)  # Incoterm, Franchise
        sheet.set_column('L:L', 8)   # Rest
        sheet.set_column('M:M', 25)  # Container
        sheet.set_column('N:N', 12)  # ETA
        sheet.set_column('O:O', 20)  # Observation

        # En-têtes (Ligne 4 dans votre fichier type généralement, ici ligne 0)
        headers = [
            "IMPORTER", "EXPORTER", "FCL", "INV/ CONTRACT", "PRODUCT", "DETAILS",
            "WEIGHT", "U.P", "TOTAL", "INCOTERM", "FRANCHISE", "REST", "CONTAINER", "ETA", "OBSERVATIONS"
        ]
        sheet.write_row(0, 0, headers, header_style)

        row = 1
        # On trie par exportateur pour pouvoir faire des sous-totaux si nécessaire
        # Ici on boucle sur les records sélectionnés
        
        # Groupement par exportateur pour calculer les totaux FCL et Montant par bloc
        exporters = self.mapped('supplier_id')
        
        grand_total_amount = 0.0

        for exporter in exporters:
            recs = self.filtered(lambda r: r.supplier_id == exporter)
            exporter_start_row = row + 1
            
            for rec in recs:
                sheet.write(row, 0, rec.ste_id.name or "", cell_style)
                sheet.write(row, 1, rec.supplier_id.name or "", cell_style)
                
                # Nombre de conteneurs (si vous avez un champ, sinon 1 par défaut)
                fcl_count = len(rec.container_names.split(',')) if rec.container_names else 1
                sheet.write(row, 2, fcl_count, cell_style)
                
                sheet.write(row, 3, rec.invoice_number or rec.contract_num or "", cell_style)
                sheet.write(row, 4, rec.achat_article_id.name or "", cell_style)
                sheet.write(row, 5, rec.details or "", cell_style)
                sheet.write(row, 6, float(rec.weight or 0.0), num_style)
                sheet.write(row, 7, float(rec.price_unit or 0.0), num_style)
                sheet.write(row, 8, float(rec.amount_total or 0.0), num_style)
                sheet.write(row, 9, rec.incoterm or "", cell_style)
                sheet.write(row, 10, rec.free_time or "", cell_style)
                sheet.write(row, 11, "", cell_style) # REST (Calculé ou vide)
                sheet.write(row, 12, rec.container_names or "", cell_style)
                
                if rec.eta:
                    sheet.write_datetime(row, 13, datetime.combine(rec.eta, time.min), date_style)
                else:
                    sheet.write(row, 13, "", cell_style)
                
                sheet.write(row, 14, rec.exit_comment or "", cell_style)
                
                grand_total_amount += float(rec.amount_total or 0.0)
                row += 1

            # Ligne de sous-total par Exportateur (Comme dans votre fichier)
            sheet.write(row, 1, "TOTAL FCL", total_row_style)
            # Somme FCL
            sheet.write_formula(row, 2, f'=SUM(C{exporter_start_row}:C{row})', total_row_style)
            # Espace vide
            for c in range(3, 7): sheet.write(row, c, "", total_row_style)
            sheet.write(row, 7, "TOTAL", total_row_style)
            # Somme Montant
            sheet.write_formula(row, 8, f'=SUM(I{exporter_start_row}:I{row})', total_row_style)
            for c in range(9, 15): sheet.write(row, c, "", total_row_style)
            row += 1

        # Ligne Finale Grand Total
        row += 1
        sheet.merge_range(row, 0, row, 7, "TOTAL GÉNÉRAL", total_row_style)
        sheet.write(row, 8, grand_total_amount, total_row_style)

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': "SUIVI_WEEK_LOGISTIQUE.xlsx",
            'datas': file_data,
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
