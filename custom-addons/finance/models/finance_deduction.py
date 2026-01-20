from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import io
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class FinanceDeductionAccount(models.Model):
    _name = 'finance.deduction.account'
    _description = 'Compte de Déduction'
    _rec_name = 'display_name'

    ste_id = fields.Many2one('finance.ste', string='Société', required=True, tracking=True)
    benif_id = fields.Many2one('finance.benif', string='Bénéficiaire', required=True, tracking=True, domain="[('benif_deduction', '=', True)]")
    
    deposit_ids = fields.One2many('finance.deduction.deposit', 'account_id', string='Dépôts')
    payment_ids = fields.One2many('finance.deduction.payment', 'account_id', string='Paiements')
    
    total_deposited = fields.Float(string='Total Déposé', compute='_compute_balance', store=True)
    total_deducted = fields.Float(string='Total Déduit', compute='_compute_balance', store=True)
    balance = fields.Float(string='Solde Restant', compute='_compute_balance', store=True)

    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('unique_ste_benif', 'unique(ste_id, benif_id)', 'Un compte de déduction existe déjà pour ce couple Société / Bénéficiaire.')
    ]

    @api.depends('ste_id', 'benif_id')
    def _compute_display_name(self):
        for rec in self:
            ste = rec.ste_id.name if rec.ste_id else '?'
            benif = rec.benif_id.name if rec.benif_id else '?'
            rec.display_name = f"{ste} ↔ {benif}"

    @api.depends('deposit_ids.amount', 'payment_ids.amount')
    def _compute_balance(self):
        for rec in self:
            total_dep = sum(d.amount for d in rec.deposit_ids)
            total_ded = sum(p.amount for p in rec.payment_ids)
            rec.total_deposited = total_dep
            rec.total_deducted = total_ded
            rec.balance = total_dep - total_ded



    def action_export_deduction_excel(self):
        self.ensure_one()

        if not xlsxwriter:
            raise ValidationError("The library xlsxwriter is not installed.")

        from datetime import datetime, time

        def to_xlsx_date(d):
            """Convert Odoo Date (date) to datetime for xlsxwriter; return None if empty."""
            if not d:
                return None
            # d is a python date object (fields.Date)
            return datetime.combine(d, time.min)

        # Selection label helper (avoid FALSE for empty selection)
        type_label = dict(self.env['finance.deduction.payment']._fields['type'].selection)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # =========================
        # Styles
        # =========================
        title_style = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        section_style = workbook.add_format({'bold': True, 'font_size': 12, 'bg_color': '#f2f2f2', 'border': 1})
        header_style = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#f2f2f2'})
        cell_style = workbook.add_format({'border': 1})
        money_style = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        date_style = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})

        # =========================
        # Single Sheet
        # =========================
        sheet = workbook.add_worksheet("Deduction Details")
        sheet.set_column(0, 0, 18)  # Date
        sheet.set_column(1, 1, 16)  # Amount
        sheet.set_column(2, 2, 18)  # Reference/Type
        sheet.set_column(3, 3, 22)  # Operation Ref / BL
        sheet.set_column(4, 4, 28)  # Beneficiary / Containers
        # Title
        sheet.merge_range('A1:E1', 'Deduction Account Details', title_style)

        row = 2

        # =========================
        # Summary block
        # =========================
        sheet.merge_range(row, 0, row, 5, 'Summary', section_style)
        row += 1

        summary = [
            ("Company", self.ste_id.name or ""),
            ("Beneficiary", self.benif_id.name or ""),
            ("Total Deposited", self.total_deposited or 0.0),
            ("Total Deducted", self.total_deducted or 0.0),
            ("Remaining Balance", self.balance or 0.0),
        ]

        for label, value in summary:
            sheet.write(row, 0, label, header_style)
            if isinstance(value, (int, float)):
                sheet.write_number(row, 1, float(value), money_style)
            else:
                sheet.write(row, 1, value or "", cell_style)
            row += 1

        row += 2  # blank lines

        # =========================
        # Deposits section
        # =========================
        sheet.merge_range(row, 0, row, 5, 'Deposits', section_style)
        row += 1

        dep_headers = ["Date", "Amount", "Reference", "Comment", "", ""]
        sheet.write_row(row, 0, dep_headers, header_style)
        row += 1

        for dep in self.deposit_ids.sorted(key=lambda x: (x.date or fields.Date.today())):
            dt = to_xlsx_date(dep.date)
            if dt:
                sheet.write_datetime(row, 0, dt, date_style)
            else:
                sheet.write(row, 0, "", cell_style)

            sheet.write_number(row, 1, float(dep.amount or 0.0), money_style)
            sheet.write(row, 2, dep.reference or "", cell_style)
            sheet.write(row, 3, dep.comment or "", cell_style)
            # keep remaining columns empty
            sheet.write(row, 4, "", cell_style)
            sheet.write(row, 5, "", cell_style)
            row += 1

        row += 2  # blank lines

        # =========================
        # Deductions / Payments section
        # =========================
        sheet.merge_range(row, 0, row, 5, 'Deductions (Payments)', section_style)
        row += 1

        pay_headers = ["Date", "Amount", "Type", "Operation Ref", "BL"]
        sheet.write_row(row, 0, pay_headers, header_style)
        row += 1

        for pay in self.payment_ids.sorted(key=lambda x: (x.date or fields.Date.today())):
            dt = to_xlsx_date(pay.date)
            if dt:
                sheet.write_datetime(row, 0, dt, date_style)
            else:
                sheet.write(row, 0, "", cell_style)

            sheet.write_number(row, 1, float(pay.amount or 0.0), money_style)

            # ✅ show label instead of technical value; keep empty instead of FALSE
            sheet.write(row, 2, type_label.get(pay.type, "") if pay.type else "", cell_style)

            sheet.write(row, 3, pay.operation_ref or "", cell_style)
            sheet.write(row, 4, pay.bl_id.name if pay.bl_id else "", cell_style)
            row += 1

        workbook.close()
        output.seek(0)

        file_data = base64.b64encode(output.read())
        output.close()

        filename = f"Deduction_{(self.ste_id.name or '').strip()}_{(self.benif_id.name or '').strip()}.xlsx"

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': file_data,
            'type': 'binary',
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }



class FinanceDeductionDeposit(models.Model):
    _name = 'finance.deduction.deposit'
    _description = 'Dépôt (Avance)'
    _order = 'date desc, id desc'

    account_id = fields.Many2one('finance.deduction.account', string='Compte', required=True, ondelete='cascade')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    amount = fields.Float(string='Montant', required=True)
    reference = fields.Selection([
        ('virement', 'Virement'),
        ('cash', 'Espèce'),
        ('chq', 'Chèque'),
    ], string='Référence', required=True)
    comment = fields.Text(string='Commentaire')

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError("Le montant du dépôt doit être positif.")


class FinanceDeductionPayment(models.Model):
    _name = 'finance.deduction.payment'
    _description = 'Paiement par Déduction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    # Relation logic: User picks Ste + Benif -> System finds Account
    ste_id = fields.Many2one('finance.ste', string='Société', required=True, tracking=True)
    benif_id = fields.Many2one('finance.benif', string='Bénéficiaire', required=True, tracking=True, domain="[('benif_deduction', '=', True)]")
    
    account_id = fields.Many2one('finance.deduction.account', string='Compte de Déduction', compute='_compute_account_id', store=True, readonly=True)

    date = fields.Date(string='Date Opération', default=fields.Date.context_today, required=True, tracking=True)
    amount = fields.Float(string='Montant Déduit', required=True, tracking=True)
    operation_ref = fields.Char(string='Référence Opération / Facture', required=True, tracking=True)
    note = fields.Text(string='Note')

    type = fields.Selection([
        ('magasinage', 'Magasinage'),
        ('surestarie', 'Surestarie'),
        ('change', 'Change'),
        ('inspection', 'Inspection'),
    ], string='Type', required=True, tracking=True)

    bl_id = fields.Many2one(
        'logistique.dossier', 
        string='BL',
        required=True,
        tracking=True
    )

    container_ids = fields.One2many(
        related='bl_id.container_ids',
        string='Conteneurs',
        readonly=True
    )

    @api.depends('ste_id', 'benif_id')
    def _compute_account_id(self):
        for rec in self:
            if rec.ste_id and rec.benif_id:
                account = self.env['finance.deduction.account'].search([
                    ('ste_id', '=', rec.ste_id.id),
                    ('benif_id', '=', rec.benif_id.id)
                ], limit=1)
                rec.account_id = account
            else:
                rec.account_id = False

    @api.model
    def create(self, vals):
        # 1. Resolve Account Check
        ste_id = vals.get('ste_id')
        benif_id = vals.get('benif_id')
        amount = vals.get('amount', 0)

        # Basic Checks
        if amount <= 0:
            raise ValidationError("Le montant de la déduction doit être strictement positif.")

        # Find Account
        account = self.env['finance.deduction.account'].search([
            ('ste_id', '=', ste_id),
            ('benif_id', '=', benif_id)
        ], limit=1)

        if not account:
            # Try to get names for error message
            ste_name = self.env['finance.ste'].browse(ste_id).name
            benif_name = self.env['finance.benif'].browse(benif_id).name
            raise ValidationError(f"Aucun compte de déduction trouvé pour {ste_name} ↔ {benif_name}.\nVeuillez d'abord créer ce compte et y ajouter des fonds.")

        # 2. Strict Balance Check
        # Available = Balance (Stored)
        # Note: If concurrent creating, this might be race-condition prone but Odoo handles transactions.
        # Ideally we compute current balance from DB to be checking against most recent state.
        
        if account.balance < amount:
            raise ValidationError(
                f"🚫 Solde insuffisant pour ce paiement.\n\n"
                f"Compte : {account.display_name}\n"
                f"Solde disponible : {account.balance:,.2f}\n"
                f"Montant demandé : {amount:,.2f}\n\n"
                "Veuillez créditer le compte avant de passer ce paiement."
            )

        return super().create(vals)


