from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import io
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class Cal3iyaClient(models.Model):
    _name = 'finance.benif'
    _description = 'Bénificiaires'

    name = fields.Char(string='Bénificiaire', required=True)
    days = fields.Integer(string='Jours de plus')
    type = fields.Selection([
        ('import', 'Importation'),
        ('divers', 'Divers'),
        ('bureau', 'Bureau'),
        ('annule', 'Annulé'),
        ], string='Imp/Div', required=True, store=True)

    benif_deduction = fields.Boolean(string="Autorise Paiement par Déduction", default=False)

    physical_chq_ids = fields.One2many(
        'finance.cheque.physical',
        'benif_id',
        string="Chèques Physiques"
    )
    
    effet_ids = fields.One2many(
        'finance.effet',
        'benif_id',
        string="Effets"
    )

    total_credit = fields.Float(string="Total Crédit", compute="_compute_chq_totals")
    total_debit = fields.Float(string="Total Encaissé", compute="_compute_chq_totals")
    solde = fields.Float(string="Solde à ce jour", compute="_compute_chq_totals")

    @api.depends('physical_chq_ids.credit', 'physical_chq_ids.debit', 'effet_ids.montant', 'effet_ids.date_encaissement')
    def _compute_chq_totals(self):
        for rec in self:
            c_credit = sum(rec.physical_chq_ids.mapped('credit'))
            e_credit = sum(rec.effet_ids.mapped('montant'))
            rec.total_credit = c_credit + e_credit
            
            c_debit = sum(rec.physical_chq_ids.mapped('debit'))
            e_debit = sum(e.montant for e in rec.effet_ids if e.date_encaissement)
            rec.total_debit = c_debit + e_debit
            
            rec.solde = rec.total_credit - rec.total_debit

    def get_financial_breakdown(self):
        """
        Returns a list of dicts for the report:
        [{'ste': 'Company Name', 'encaisse': 100.0, 'non_encaisse': 50.0, 'count_encaisse': 1, 'count_non_encaisse': 1}]
        """
        self.ensure_one()
        breakdown = {}
        encours_only = self.env.context.get('encours_only')
        for chq in self.physical_chq_ids:
            if encours_only and chq.date_encaissement:
                continue

            ste_name = chq.ste_id.name or 'Inconnue'
            if ste_name not in breakdown:
                breakdown[ste_name] = {
                    'encaisse': 0.0, 
                    'non_encaisse': 0.0,
                    'count_encaisse': 0,
                    'count_non_encaisse': 0
                }
            
            if chq.date_encaissement:
                breakdown[ste_name]['encaisse'] += chq.amount_total
                breakdown[ste_name]['count_encaisse'] += 1
            else:
                breakdown[ste_name]['non_encaisse'] += chq.amount_total
                breakdown[ste_name]['count_non_encaisse'] += 1
                
        for effet in self.effet_ids:
            if encours_only and effet.date_encaissement:
                continue

            ste_name = effet.ste_id.name or 'Inconnue'
            if ste_name not in breakdown:
                breakdown[ste_name] = {
                    'encaisse': 0.0, 
                    'non_encaisse': 0.0,
                    'count_encaisse': 0,
                    'count_non_encaisse': 0
                }
            if effet.date_encaissement:
                breakdown[ste_name]['encaisse'] += effet.montant
                breakdown[ste_name]['count_encaisse'] += 1
            else:
                breakdown[ste_name]['non_encaisse'] += effet.montant
                breakdown[ste_name]['count_non_encaisse'] += 1
        
        # Convert to list for easier iteration in QWeb
        result = []
        for ste, values in breakdown.items():
            result.append({
                'ste': ste,
                'encaisse': values['encaisse'],
                'non_encaisse': values['non_encaisse'],
                'count_encaisse': values['count_encaisse'],
                'count_non_encaisse': values['count_non_encaisse'],
                'total': values['encaisse'] + values['non_encaisse'],
                'count_total': values['count_encaisse'] + values['count_non_encaisse']
            })
        return result

    def get_cheque_stats(self):
        """Returns global statistics about cheque and effet counts."""
        self.ensure_one()
        encours_only = self.env.context.get('encours_only')

        chqs = self.physical_chq_ids
        effets = self.effet_ids
        if encours_only:
            chqs = chqs.filtered(lambda c: not c.date_encaissement)
            effets = effets.filtered(lambda e: not e.date_encaissement)
            
        total_chqs = len(chqs) + len(effets)
        encaisse_chqs = len(chqs.filtered(lambda c: c.date_encaissement)) + len(effets.filtered(lambda e: e.date_encaissement))
        non_encaisse_chqs = total_chqs - encaisse_chqs
        return {
            'total': total_chqs,
            'encaisse': encaisse_chqs,
            'non_encaisse': non_encaisse_chqs
        }

    def get_detailed_cheques(self):
        """Returns detailed information for each physical cheque for the report."""
        self.ensure_one()
        detailed_chqs = []
        facture_labels = {'m': 'M', 'bureau': 'Bureau', 'fact': 'F/', 'annule': 'Annulé'}
        encours_only = self.env.context.get('encours_only')
        
        for chq in self.physical_chq_ids:
            if encours_only and chq.date_encaissement:
                continue

            # Aggregate data from splits
            factures = []
            persons = []
            types = []
            
            for dc in chq.datacheque_ids:
                # Facture
                if dc.facture == 'fact':
                    factures.append(dc.serie or 'F/')
                else:
                    factures.append(facture_labels.get(dc.facture, dc.facture or ''))
                
                # Person
                if dc.perso_id and dc.perso_id.name not in persons:
                    persons.append(dc.perso_id.name)
                
                # Type
                if dc.type:
                    type_label = dict(dc._fields['type'].selection).get(dc.type, dc.type)
                    if type_label not in types:
                        types.append(type_label)

            detailed_chqs.append({
                'name': chq.name,
                'ste': chq.ste_id.name if chq.ste_id else '',
                'date_emission': chq.date_emission,
                'date_echeance': chq.date_echeance,
                'date_encaissement': chq.date_encaissement,
                'amount': chq.amount_total,
                'status': 'Encaissé' if chq.date_encaissement else 'Non encaissé',
                'factures': ', '.join(filter(None, factures)),
                'persons': ', '.join(filter(None, persons)),
                'types': ', '.join(filter(None, types)),
            })
            
        for effet in self.effet_ids:
            if encours_only and effet.date_encaissement:
                continue

            if effet.is_annule:
                s_label = 'Annulé'
            elif effet.date_encaissement:
                s_label = 'Encaissé'
            else:
                s_label = 'Non encaissé'
                
            detailed_chqs.append({
                'name': 'EFFET ' + str(effet.serie or ''),
                'ste': effet.ste_id.name if effet.ste_id else '',
                'date_emission': effet.date_emission,
                'date_echeance': effet.date_echeance,
                'date_encaissement': effet.date_encaissement,
                'amount': effet.montant,
                'status': s_label,
                'factures': '',
                'persons': '',
                'types': 'Effet',
            })
        
        # Sort by company (case-insensitive) first, then by date echeance
        return sorted(detailed_chqs, key=lambda x: ((x['ste'] or '').lower(), x['date_echeance'] or fields.Date.today()))

    def action_export_excel(self):
        self.ensure_one()
        if not xlsxwriter:
            raise ValidationError("The library xlsxwriter is not installed.")

        from datetime import datetime, time

        def to_xlsx_date(d):
            if not d:
                return None
            return datetime.combine(d, time.min)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Styles
        title_style = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        section_style = workbook.add_format({'bold': True, 'font_size': 12, 'bg_color': '#f2f2f2', 'border': 1})
        header_style = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#f2f2f2', 'valign': 'vcenter'})
        cell_style = workbook.add_format({'border': 1, 'valign': 'top'})
        money_style = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'valign': 'top'})
        date_style = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy', 'valign': 'top'})
        wrap_style = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'top'})

        sheet = workbook.add_worksheet("Détails Bénéficiaire")
        
        # Colonnes (13 colonnes total: 0 à 12)
        sheet.set_column(0, 0, 15)  # N° Chèque
        sheet.set_column(1, 1, 20)  # Société
        sheet.set_column(2, 2, 15)  # Date d'émission
        sheet.set_column(3, 3, 15)  # Date d'échéance
        sheet.set_column(4, 4, 15)  # Date d'encaissement
        sheet.set_column(5, 5, 20)  # Facture
        sheet.set_column(6, 6, 20)  # Personne
        sheet.set_column(7, 7, 15)  # Type
        sheet.set_column(8, 8, 12)  # Journal
        sheet.set_column(9, 9, 15)  # BL
        sheet.set_column(10, 10, 12) # État
        sheet.set_column(11, 11, 15) # Crédit
        sheet.set_column(12, 12, 15) # Débit

        # Titre Principal
        sheet.merge_range('A1:M1', f"Situation du Bénéficiaire : {self.name}", title_style)

        # Date de relevé à droite
        from odoo import fields as odoo_fields
        sheet.write('L4', 'Date', header_style)
        sheet.write('M4', odoo_fields.Date.today().strftime('%d/%m/%Y'), cell_style)

        row = 2

        # -------------------------
        # Bloc Résumé
        # -------------------------
        sheet.merge_range(row, 0, row, 12, "Informations Générales", section_style)
        row += 1

        summary = [
            ("Nom", self.name or ""),
            ("Autorise Déduction", "Oui" if self.benif_deduction else "Non"),
            ("Total Crédit", self.total_credit or 0.0),
            ("Total Encaissé", self.total_debit or 0.0),
            ("Solde", self.solde or 0.0),
        ]

        for label, value in summary:
            sheet.write(row, 0, label, header_style)
            if isinstance(value, (int, float)):
                sheet.write_number(row, 1, float(value), money_style)
            else:
                sheet.write(row, 1, value or "", cell_style)
            row += 1

        row += 2  # Espace

        # -------------------------
        # Bloc Liste des Chèques / Effets
        # -------------------------
        has_chqs = bool(self.physical_chq_ids)
        has_effets = bool(self.effet_ids)
        doc_label_title = "Documents" if (has_chqs and has_effets) else ("Effets" if has_effets else "Chèques Physiques")
        num_label = "N° Document" if (has_chqs and has_effets) else ("N° Effet" if has_effets else "N° Chèque")

        sheet.merge_range(row, 0, row, 12, f"Détails des {doc_label_title}", section_style)
        row += 1

        headers = [
            num_label, "Société", "Date d'émission", "Date d'échéance",
            "Date d'encaissement", "Facture", "Personne", "Type", 
            "Journal", "BL", "État", "Crédit", "Débit"
        ]
        sheet.write_row(row, 0, headers, header_style)
        row += 1

        facture_labels = {'m': 'M', 'bureau': 'Bureau', 'fact': 'F/', 'annule': 'Annulé'}

        for chq in self.physical_chq_ids:
            # Numéro
            sheet.write(row, 0, chq.name or "", cell_style)
            # Société
            sheet.write(row, 1, chq.ste_id.name if chq.ste_id else "", cell_style)
            
            # Dates
            dt_em = to_xlsx_date(chq.date_emission)
            if dt_em: sheet.write_datetime(row, 2, dt_em, date_style)
            else: sheet.write(row, 2, "", cell_style)

            dt_ech = to_xlsx_date(chq.date_echeance)
            if dt_ech: sheet.write_datetime(row, 3, dt_ech, date_style)
            else: sheet.write(row, 3, "", cell_style)

            dt_enc = to_xlsx_date(chq.date_encaissement)
            if dt_enc: sheet.write_datetime(row, 4, dt_enc, date_style)
            else: sheet.write(row, 4, "", cell_style)

            # Aggregated fields from splits
            fact_list = []
            perso_list = []
            type_list = []
            journal_list = []
            bl_list = []
            state_list = []

            for dc in chq.datacheque_ids:
                # Facture
                if dc.facture == 'fact':
                    fact_list.append(dc.serie or 'F/')
                else:
                    fact_list.append(facture_labels.get(dc.facture, dc.facture or ''))
                
                # Personne
                if dc.perso_id and dc.perso_id.name not in perso_list:
                    perso_list.append(dc.perso_id.name)
                
                # Type
                if dc.type:
                    t_label = dict(dc._fields['type'].selection).get(dc.type, dc.type)
                    if t_label not in type_list:
                        type_list.append(t_label)
                
                # Journal
                if str(dc.journal) not in journal_list:
                    journal_list.append(str(dc.journal))
                
                # BL
                if dc.bl and dc.bl not in bl_list:
                    bl_list.append(dc.bl)
                
                # State
                s_label = dict(dc._fields['state'].selection).get(dc.state, dc.state)
                if s_label not in state_list:
                    state_list.append(s_label)

            sheet.write(row, 5, '\n'.join(filter(None, fact_list)), wrap_style)
            sheet.write(row, 6, '\n'.join(filter(None, perso_list)), wrap_style)
            sheet.write(row, 7, '\n'.join(filter(None, type_list)), wrap_style)
            sheet.write(row, 8, '\n'.join(filter(None, journal_list)), wrap_style)
            sheet.write(row, 9, '\n'.join(filter(None, bl_list)), wrap_style)
            sheet.write(row, 10, '\n'.join(filter(None, state_list)), wrap_style)

            # Montants
            sheet.write_number(row, 11, float(chq.credit or 0.0), money_style)
            sheet.write_number(row, 12, float(chq.debit or 0.0), money_style)

            row += 1
            
        for effet in self.effet_ids:
            # Numéro
            sheet.write(row, 0, 'EFFET ' + str(effet.serie or ''), cell_style)
            # Société
            sheet.write(row, 1, effet.ste_id.name if effet.ste_id else "", cell_style)
            
            # Dates
            dt_em = to_xlsx_date(effet.date_emission)
            if dt_em: sheet.write_datetime(row, 2, dt_em, date_style)
            else: sheet.write(row, 2, "", cell_style)

            dt_ech = to_xlsx_date(effet.date_echeance)
            if dt_ech: sheet.write_datetime(row, 3, dt_ech, date_style)
            else: sheet.write(row, 3, "", cell_style)

            dt_enc = to_xlsx_date(effet.date_encaissement)
            if dt_enc: sheet.write_datetime(row, 4, dt_enc, date_style)
            else: sheet.write(row, 4, "", cell_style)

            sheet.write(row, 5, '', cell_style) # Facture
            sheet.write(row, 6, '', cell_style) # Personne
            sheet.write(row, 7, 'Effet', cell_style) # Type
            sheet.write(row, 8, '', cell_style) # Journal
            sheet.write(row, 9, '', cell_style) # BL
            
            if effet.is_annule:
                s_label = 'Annulé'
            elif effet.date_encaissement:
                s_label = 'Encaissé'
            else:
                s_label = 'Non encaissé'
                
            sheet.write(row, 10, s_label, cell_style) # État

            # Montants
            credit = effet.montant or 0.0
            debit = effet.montant if effet.date_encaissement else 0.0
            sheet.write_number(row, 11, float(credit), money_style)
            sheet.write_number(row, 12, float(debit), money_style)

            row += 1

        workbook.close()
        output.seek(0)

        file_data = base64.b64encode(output.read())
        output.close()

        sanitized_name = "".join(c for c in (self.name or "") if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"Detail_Beneficiaire_{sanitized_name}.xlsx"

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