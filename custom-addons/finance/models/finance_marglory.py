from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import io
import base64
from datetime import datetime

class FinanceMarglory(models.Model):
    _name = 'finance.marglory'
    _description = 'Finance Marglory'
    _rec_name = 'bl_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # -------------------------------------------------------------------------
    # SOURCE OF TRUTH (Douane / Logistique)
    # -------------------------------------------------------------------------
    douane_id = fields.Many2one(
        'logistique.entry',
        string='Dossier Douane',
        required=True,
        ondelete='cascade',
        tracking=True,
        index=True
    )

    # -------------------------------------------------------------------------
    # READ-ONLY FIELDS (Related to Douane)
    # -------------------------------------------------------------------------
    bl_number = fields.Char(related='douane_id.bl_number', string='BL Number', store=True, readonly=True)
    supplier_id = fields.Many2one(related='douane_id.supplier_id', string='Fournisseur', store=True, readonly=True)
    ste_id = fields.Many2one(related='douane_id.ste_id', string='Société', store=True, readonly=True)
    
    dum = fields.Char(related='douane_id.dum', string='N° DUM', store=True, readonly=True)
    eta = fields.Date(related='douane_id.eta', string='ETA', store=True, readonly=True)
    
    container_ids = fields.One2many(related='douane_id.container_ids', string='Conteneurs', readonly=True)

    # -------------------------------------------------------------------------
    # FINANCE FIELDS (Editable)
    # -------------------------------------------------------------------------
    dossier_reglement = fields.Char(
        string="Réglement N°",
        tracking=True
    )
    journal = fields.Integer(string='Journal', tracking=True)
    type = fields.Selection([
        ('THC', 'THC'),
        ('FRET', 'FRET'),
        ('ASSURANCE', 'Assurance')
    ], string="Type", required=True, default='THC', tracking=True)
    
    facture_marglory = fields.Char(string='Facture Marglory', tracking=True, required=True)
    scan_marglory = fields.Char(string='Scan Facture (Drive)', required=True, tracking=True)
    
    amount = fields.Float(string='Montant Total', required=True, tracking=True)

    # -------------------------------------------------------------------------
    # PAYMENT LINK
    # -------------------------------------------------------------------------
    payment_id = fields.Many2one(
        'finance.marglory.payment', 
        string='Paiement', 
        readonly=True, 
        tracking=True,
        ondelete='set null'
    )

    # -------------------------------------------------------------------------
    # CHEQUE INFO (Read-only from Payment)
    # -------------------------------------------------------------------------
    cheque_id = fields.Many2one(related='payment_id.physical_cheque_id', string='Chèque', store=False, readonly=True)
    cheque_number = fields.Char(related='cheque_id.name', string='N° Chèque', readonly=True)
    cheque_date_emission = fields.Date(related='cheque_id.date_emission', string="Date d'émission", readonly=True)
    cheque_date_echeance = fields.Date(related='cheque_id.date_echeance', string="Date d'échéance", readonly=True)
    cheque_date_limite = fields.Date(related='cheque_id.date_limite', string="D. limite", readonly=True)
    cheque_amount = fields.Float(related='cheque_id.amount_total', string="Montant chq", readonly=True)
    cheque_encours = fields.Selection(related='cheque_id.encours', string="D. Encaissement", readonly=True)
    
    fac_comm = fields.Char(related='douane_id.invoice_number', string="Fac comm", readonly=True)
    article_id = fields.Many2one(related='douane_id.achat_article_id', string="Article", readonly=True)
    
    is_encaisse = fields.Boolean(string='Encaissé', compute='_compute_is_encaisse', store=True)

    # -------------------------------------------------------------------------
    # COMPUTED FIELDS
    # -------------------------------------------------------------------------
    scan_marglory_url = fields.Char(string="Lien Scan", compute="_compute_scan_url")
    container_names = fields.Char(string="Conteneurs", compute="_compute_container_names", store=True)

    _sql_constraints = [
        ('douane_id_type_uniq', 'unique (douane_id, type)', 'Un dossier Marglory de ce type existe déjà pour ce dossier Douane !')
    ]

    @api.depends('cheque_id.encours')
    def _compute_is_encaisse(self):
        for rec in self:
            rec.is_encaisse = (rec.cheque_id.encours == 'encaisse')

    @api.depends('scan_marglory')
    def _compute_scan_url(self):
        for rec in self:
            if rec.scan_marglory:
                if rec.scan_marglory.startswith('http'):
                    rec.scan_marglory_url = rec.scan_marglory
                else:
                    rec.scan_marglory_url = 'https://' + rec.scan_marglory
            else:
                rec.scan_marglory_url = False

    @api.depends('douane_id.container_ids.name')
    def _compute_container_names(self):
        for rec in self:
            rec.container_names = ', '.join(rec.douane_id.container_ids.mapped('name'))

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('scan_marglory')
    def _check_scan_marglory_required(self):
        for rec in self:
            if not rec.scan_marglory or not rec.scan_marglory.strip():
                raise ValidationError("Le lien du scan est obligatoire. Merci de le renseigner.")
    @api.constrains('amount')
    def _check_positive_amount(self):
        for rec in self:
            if rec.amount < 0:
                raise ValidationError("Le montant doit être positif.")

    @api.constrains('payment_id')
    def _check_single_payment(self):
        for rec in self:
            if rec.payment_id:
                # Ensure no other invoice links to the same payment if logic dictated 1-to-1, 
                # but requirement is 1 cheque -> many invoices, 1 invoice -> 1 cheque.
                # The Many2one field already enforces 1 invoice -> 1 cheque.
                # We just need to ensure we don't accidentally over-write or link if typically restricted?
                # Actually, Many2one is enough structure-wise.
                # But let's check if there's any weird state.
                pass

    def write(self, vals):
        # Backend protection: Prevent changing payment if already paid
        if 'payment_id' in vals:
            for rec in self:
                if rec.payment_id and vals['payment_id'] != rec.payment_id.id:
                    # Allow removing payment (setting to False) if needed? 
                    if vals['payment_id']:
                         raise ValidationError("Impossible de modifier le paiement d'une facture déjà payée. Veuillez d'abord annuler le paiement existant.")
        return super(FinanceMarglory, self).write(vals)

    def unlink(self):
        return super(FinanceMarglory, self).unlink()

    def action_export_excel(self):
        """
        Exports the selected Marglory records to an Excel file formatted like the user's requested layout.
        """
        import xlsxwriter

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Marglory Report")

        # Styles
        header_style = workbook.add_format({
            'bold': True, 'bg_color': '#FFFF00', 'border': 1, 'align': 'center', 'valign': 'vcenter'
        })
        cell_style = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        date_style = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': 'dd/mm/yyyy'})
        money_style = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '#,##0.00'})
        red_bg_style = workbook.add_format({'bold': True, 'bg_color': '#FF0000', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        red_font_style = workbook.add_format({'bold': True, 'font_color': '#FF0000', 'border': 1, 'align': 'center', 'valign': 'vcenter'})

        # Write top right date
        sheet.write('L1', datetime.now().strftime('%d/%m/%Y'), red_bg_style)

        # Columns configuration
        columns = [
            ("SN", 10), ("11", 10), ("N° Chèque", 15), ("A l'ordre de", 20),
            ("MT. CHQ", 15), ("Type", 12), ("D. Encaisse", 12), ("D. limite", 12),
            ("Echéance", 12), ("Fournisseur", 20), ("Article", 15), ("Fac comm", 15)
        ]

        for col_num, (col_name, col_width) in enumerate(columns):
            sheet.write(1, col_num, col_name, header_style)
            sheet.set_column(col_num, col_num, col_width)

        row = 2
        total_amount = 0.0

        for rec in self:
            # Gather data
            ste_name = rec.ste_id.name if rec.ste_id else "SN"
            journal = str(rec.journal) if rec.journal else ""
            
            chq = rec.payment_id.physical_cheque_id
            chq_name = chq.name if chq else ""
            benif_name = chq.benif_id.name if chq and chq.benif_id else "MARGLORY"
            amount = rec.amount or 0.0
            total_amount += amount
            
            m_type = rec.type or ""
            if m_type == 'FRET':
                type_style = red_bg_style
            else:
                type_style = cell_style
                
            splits = chq.datacheque_ids if chq else []
            d_encaisse = splits[0].date_encaissement if splits and splits[0].date_encaissement else False
            d_limite = splits[0].date_limite if splits and splits[0].date_limite else False
            echeance = chq.date_echeance if chq else False
            
            fournisseur = rec.supplier_id.name if rec.supplier_id else ""
            article = rec.douane_id.article_id.name if rec.douane_id and rec.douane_id.article_id else ""
            fac_comm = rec.douane_id.invoice_number if rec.douane_id else ""

            # Write row
            sheet.write(row, 0, ste_name, cell_style)
            sheet.write(row, 1, journal, cell_style)
            sheet.write(row, 2, chq_name, cell_style)
            sheet.write(row, 3, benif_name, cell_style)
            sheet.write_number(row, 4, amount, money_style)
            sheet.write(row, 5, m_type, type_style)
            
            if d_encaisse:
                sheet.write_datetime(row, 6, d_encaisse, date_style)
            else:
                sheet.write(row, 6, "N", cell_style)
                
            if d_limite:
                sheet.write_datetime(row, 7, d_limite, date_style)
            else:
                sheet.write(row, 7, "", cell_style)
                
            if echeance:
                sheet.write_datetime(row, 8, echeance, red_font_style)
            else:
                sheet.write(row, 8, "", red_font_style)
                
            sheet.write(row, 9, fournisseur, red_font_style)
            sheet.write(row, 10, article, cell_style)
            sheet.write(row, 11, fac_comm, cell_style)
            
            row += 1

        # Total row
        sheet.write(row, 3, "Total", header_style)
        sheet.write_number(row, 4, total_amount, workbook.add_format({'bold': True, 'bg_color': '#FFFF00', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '#,##0.00'}))

        workbook.close()
        output.seek(0)
        
        # Save attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'Rapport_Marglory_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'res_model': 'finance.marglory',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.bl_number or 'N/A'} - {rec.facture_marglory or 'No Facture'}"
            result.append((rec.id, name))
        return result
