from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io

try:
    import openpyxl
except ImportError:
    openpyxl = None

class SutraImportWizard(models.TransientModel):
    _name = 'sutra.import.wizard'
    _description = 'Import Factures SUTRA'

    file = fields.Binary(string='Fichier Excel', required=True)
    filename = fields.Char(string='Nom du fichier')

    def action_import(self):
        if not openpyxl:
            raise UserError("La librairie openpyxl n'est pas installée sur le serveur.")

        if not self.file:
            raise UserError("Veuillez sélectionner un fichier.")

        file_content = base64.b64decode(self.file)
        try:
            wb = openpyxl.load_workbook(filename=io.BytesIO(file_content), data_only=True)
            sheet = wb.active
        except Exception as e:
            raise UserError(f"Erreur lors de la lecture du fichier Excel: {str(e)}\nVérifiez que c'est bien un fichier .xlsx valide.")

        rows = list(sheet.iter_rows(values_only=True))
        if len(rows) < 2:
            raise UserError("Le fichier semble vide ou ne contient que l'en-tête (il faut au moins une ligne de données).")

        logs = []
        created = 0

        for idx, row in enumerate(rows[1:], start=2): # Skip header
            if not row or not any(row):
                continue
            
            dum_val = str(row[0]).strip() if row[0] else ''
            fact_val = str(row[1]).strip() if len(row) > 1 and row[1] else ''
            date_val = row[2] if len(row) > 2 else False
            
            montant_val = 0.0
            if len(row) > 3 and row[3] is not None:
                try:
                    montant_val = float(str(row[3]).replace(',', '.').replace(' ', ''))
                except ValueError:
                    montant_val = 0.0

            if not dum_val or not fact_val:
                logs.append(f"Ligne {idx}: DUM ou Numéro de Facture manquant. Ignorée.")
                continue

            # Trouver le dossier logistique via DUM
            domain = [('tanger_med_dum', '=', dum_val)]
            if 'dum' in self.env['logistique.entry']._fields:
                domain = ['|', ('dum', '=', dum_val), ('tanger_med_dum', '=', dum_val)]
            
            entries = self.env['logistique.entry'].search(domain)
            if not entries:
                logs.append(f"Ligne {idx}: DUM '{dum_val}' introuvable dans les dossiers Transit/Logistique. Ignorée.")
                continue

            entry = entries[0]

            # Trouver ou créer le dossier SUTRA
            sutra_dossier = self.env['sutra.dossier'].search([('logistics_id', '=', entry.id)], limit=1)
            if not sutra_dossier:
                sutra_dossier = self.env['sutra.dossier'].create({
                    'logistics_id': entry.id,
                })

            # Vérifier si la facture existe déjà
            existing_facture = self.env['sutra.facture'].search([
                ('sutra_id', '=', sutra_dossier.id),
                ('name', '=', fact_val)
            ], limit=1)

            if existing_facture:
                logs.append(f"Ligne {idx}: La facture '{fact_val}' existe déjà pour le DUM '{dum_val}'. Ignorée.")
                continue

            # Créer la facture
            self.env['sutra.facture'].create({
                'sutra_id': sutra_dossier.id,
                'name': fact_val,
                'date': date_val if date_val else False,
                'amount': montant_val,
                'state': 'non_paye'
            })
            created += 1

        msg = f"Import terminé avec succès.\n{created} factures créées.\n\n"
        if logs:
            msg += "Détails/Avertissements :\n" + "\n".join(logs)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Importation SUTRA',
                'message': msg,
                'type': 'success' if created > 0 else 'warning',
                'sticky': True,
            }
        }
