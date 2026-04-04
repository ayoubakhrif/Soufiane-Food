from odoo import models, fields, api, _

class GestionBuffet(models.Model):
    _name = 'gestion.buffet'
    _description = 'Gestion des Buffets'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, index=True, default=lambda self: _('Nouveau'))
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string='Statut', default='draft', tracking=True)

    client_name = fields.Char(string='Client (Personne)', required=True, tracking=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    
    place_id = fields.Many2one('buffet.place', string='Lieu', tracking=True)
    pack_id = fields.Many2one('buffet.pack', string='Pack', tracking=True)
    
    nbr_personne = fields.Integer(string='Nombre de personnes', required=True, default=1, tracking=True)
    prix_personne = fields.Float(string='Prix par personne', required=True, tracking=True)
    avance = fields.Float(string='Avance', tracking=True)

    composant_ids = fields.One2many('buffet.composant.line', 'buffet_id', string='Composants')
    charge_ids = fields.One2many('buffet.charge', 'buffet_id', string='Charges')
    division_ids = fields.One2many('buffet.division', 'buffet_id', string='Division')

    # Computed KPIs
    total_revenu = fields.Float(string='Revenu Total', compute='_compute_totals', store=True, tracking=True)
    reste_a_payer = fields.Float(string='Reste à Payer', compute='_compute_totals', store=True)
    total_charges = fields.Float(string='Coût Charges', compute='_compute_totals', store=True)
    benefice = fields.Float(string='Bénéfice', compute='_compute_totals', store=True, tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nouveau')) == _('Nouveau'):
            vals['name'] = self.env['ir.sequence'].next_by_code('gestion.buffet') or _('Nouveau')
        return super().create(vals)

    @api.onchange('pack_id')
    def _onchange_pack_id(self):
        if self.pack_id:
            self.prix_personne = self.pack_id.price_person

    @api.depends('nbr_personne', 'prix_personne', 'avance', 'charge_ids.amount')
    def _compute_totals(self):
        for rec in self:
            revenu = rec.nbr_personne * rec.prix_personne
            charges = sum(rec.charge_ids.mapped('amount'))
            
            rec.total_revenu = revenu
            rec.reste_a_payer = revenu - rec.avance
            rec.total_charges = charges
            rec.benefice = revenu - charges

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_generate_excel(self):
        self.ensure_one()
        import io
        import base64
        try:
            import xlsxwriter
        except ImportError:
            from odoo.exceptions import UserError
            raise UserError(_('La bibliothèque xlsxwriter est requise.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Détails Buffet')

        # Formats
        bold = workbook.add_format({'bold': True})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
        money_fmt = workbook.add_format({'num_format': '#,##0.00'})

        # Informations Générales
        sheet.write(0, 0, 'Référence', bold)
        sheet.write(0, 1, self.name)
        sheet.write(1, 0, 'Client', bold)
        sheet.write(1, 1, self.client_name)
        sheet.write(2, 0, 'Date', bold)
        sheet.write(2, 1, str(self.date))
        sheet.write(3, 0, 'Lieu', bold)
        sheet.write(3, 1, self.place_id.name if self.place_id else '')
        sheet.write(4, 0, 'Pack', bold)
        sheet.write(4, 1, self.pack_id.name if self.pack_id else '')

        # Détails Financiers (Head)
        sheet.write(0, 3, 'Nombre de personnes', bold)
        sheet.write(0, 4, self.nbr_personne)
        sheet.write(1, 3, 'Prix par personne', bold)
        sheet.write(1, 4, self.prix_personne, money_fmt)
        sheet.write(2, 3, 'Avance', bold)
        sheet.write(2, 4, self.avance, money_fmt)

        row = 6

        # Composants
        sheet.write(row, 0, '--- COMPOSANTS ---', bold)
        row += 1
        sheet.write(row, 0, 'Composant', header_fmt)
        sheet.write(row, 1, 'Quantité', header_fmt)
        row += 1
        for comp in self.composant_ids:
            sheet.write(row, 0, comp.composant_id.name if comp.composant_id else '')
            sheet.write(row, 1, comp.qty)
            row += 1

        row += 1

        # Charges
        sheet.write(row, 0, '--- CHARGES ---', bold)
        row += 1
        sheet.write(row, 0, 'Catégorie', header_fmt)
        sheet.write(row, 1, 'Commentaire', header_fmt)
        sheet.write(row, 2, 'Montant', header_fmt)
        row += 1
        for charge in self.charge_ids:
            sheet.write(row, 0, getattr(charge, 'categorie', ''))
            sheet.write(row, 1, charge.name or '')
            sheet.write(row, 2, charge.amount, money_fmt)
            row += 1

        row += 1

        # Division
        if self.division_ids:
            sheet.write(row, 0, '--- DIVISION DU BÉNÉFICE ---', bold)
            row += 1
            sheet.write(row, 0, 'Bénéficiaire', header_fmt)
            sheet.write(row, 1, 'Pourcentage (%)', header_fmt)
            sheet.write(row, 2, 'Part (Montant)', header_fmt)
            row += 1
            for div in self.division_ids:
                sheet.write(row, 0, div.name or '')
                sheet.write(row, 1, div.percentage)
                sheet.write(row, 2, div.amount, money_fmt)
                row += 1
            row += 1

        # Totaux
        sheet.write(row, 0, '--- RÉSUMÉ FIXE ---', bold)
        row += 1
        sheet.write(row, 0, 'Revenu Total', bold)
        sheet.write(row, 1, self.total_revenu, money_fmt)
        row += 1
        sheet.write(row, 0, 'Total Charges', bold)
        sheet.write(row, 1, self.total_charges, money_fmt)
        row += 1
        sheet.write(row, 0, 'Reste à Payer', bold)
        sheet.write(row, 1, self.reste_a_payer, money_fmt)
        row += 1
        sheet.write(row, 0, 'BÉNÉFICE NET', bold)
        sheet.write(row, 1, self.benefice, money_fmt)

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': f'Report_{self.name.replace("/", "_")}.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'gestion.buffet',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }


class BuffetComposantLine(models.Model):
    _name = 'buffet.composant.line'
    _description = 'Ligne Composant'

    buffet_id = fields.Many2one('gestion.buffet', string='Buffet', ondelete='cascade')
    composant_id = fields.Many2one('buffet.composant', string='Composant', required=True)
    qty = fields.Float(string='Nombre', required=True, default=1.0)

class BuffetCharge(models.Model):
    _name = 'buffet.charge'
    _description = 'Charge de Buffet'

    buffet_id = fields.Many2one('gestion.buffet', string='Buffet', ondelete='cascade')
    name = fields.Char(string='Commentaire')
    categorie = fields.Selection([
        ('buvette', 'Buvette'),
        ('fournisseur', 'Fournisseur'),
        ('hamala', 'Hamala'),
        ('serviants', 'Serviants'),
        ('transport', 'Transport'),
    ], string='Catégorie', required=True)
    amount = fields.Float(string='Prix', required=True, default=0.0)

class BuffetDivision(models.Model):
    _name = 'buffet.division'
    _description = 'Division du Bénéfice'

    buffet_id = fields.Many2one('gestion.buffet', string='Buffet', ondelete='cascade')
    name = fields.Char(string='Bénéficiaire', required=True)
    percentage = fields.Float(string='Pourcentage (%)', required=True, default=0.0)
    amount = fields.Float(string='Part (Montant)', compute='_compute_amount', store=True)

    @api.depends('percentage', 'buffet_id.benefice')
    def _compute_amount(self):
        for line in self:
            line.amount = (line.percentage / 100.0) * line.buffet_id.benefice
