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

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # =========================
        # Styles
        # =========================
        title_style = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center'
        })
        header_style = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#f2f2f2'
        })
        cell_style = workbook.add_format({
            'border': 1
        })
        money_style = workbook.add_format({
            'border': 1, 'num_format': '#,##0.00'
        })

        # =========================
        # Sheet 1 — Summary
        # =========================
        sheet_summary = workbook.add_worksheet("Summary")
        sheet_summary.set_column(0, 1, 30)

        sheet_summary.merge_range('A1:B1', 'Deduction Account Summary', title_style)

        data = [
            ("Company", self.ste_id.name),
            ("Beneficiary", self.benif_id.name),
            ("Total Deposited", self.total_deposited),
            ("Total Deducted", self.total_deducted),
            ("Remaining Balance", self.balance),
        ]

        row = 2
        for label, value in data:
            sheet_summary.write(row, 0, label, header_style)
            sheet_summary.write(row, 1, value, money_style if isinstance(value, float) else cell_style)
            row += 1

        # =========================
        # Sheet 2 — Deposits
        # =========================
        sheet_dep = workbook.add_worksheet("Deposits")
        sheet_dep.set_column(0, 4, 20)

        headers = ["Date", "Amount", "Reference", "Comment"]
        sheet_dep.write_row(0, 0, headers, header_style)

        row = 1
        for dep in self.deposit_ids.sorted(key=lambda x: x.date):
            sheet_dep.write(row, 0, dep.date or '', cell_style)
            sheet_dep.write(row, 1, dep.amount, money_style)
            sheet_dep.write(row, 2, dep.reference, cell_style)
            sheet_dep.write(row, 3, dep.comment or '', cell_style)
            row += 1

        # =========================
        # Sheet 3 — Payments
        # =========================
        sheet_pay = workbook.add_worksheet("Deductions")
        sheet_pay.set_column(0, 6, 22)

        headers = [
            "Date", "Amount", "Type", "Operation Ref",
            "BL", "Containers", "Note"
        ]
        sheet_pay.write_row(0, 0, headers, header_style)

        row = 1
        for pay in self.payment_ids.sorted(key=lambda x: x.date):
            sheet_pay.write(row, 0, pay.date or '', cell_style)
            sheet_pay.write(row, 1, pay.amount, money_style)
            sheet_pay.write(row, 2, pay.type, cell_style)
            sheet_pay.write(row, 3, pay.operation_ref, cell_style)
            sheet_pay.write(row, 4, pay.bl_id.name if pay.bl_id else '', cell_style)
            sheet_pay.write(row, 5, ', '.join(pay.container_ids.mapped('name')), cell_style)
            sheet_pay.write(row, 6, pay.note or '', cell_style)
            row += 1

        workbook.close()
        output.seek(0)

        file_data = base64.b64encode(output.read())
        output.close()

        filename = f"Deduction_{self.ste_id.name}_{self.benif_id.name}.xlsx"

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


