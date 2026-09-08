import os

filepath = 'custom-addons/tanger_med/models/sutra_import_batch.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_process = """
    def action_process(self):
        self.ensure_one()
        self.action_verify()
        
        ready_lines = self.line_ids.filtered(lambda l: l.status == 'ready')
        if not ready_lines:
            raise UserError("Il n'y a aucune ligne valide a traiter.")

        factures_creees = 0
        for line in ready_lines:
            # Create or get Sutra Dossier
            sutra_dossier = self.env['sutra.dossier'].search([('logistics_id', '=', line.logistics_id.id)], limit=1)
            if not sutra_dossier:
                sutra_dossier = self.env['sutra.dossier'].create({
                    'logistics_id': line.logistics_id.id,
                })
            
            # Check if invoice exists
            existing_facture = self.env['sutra.facture'].search([
                ('sutra_id', '=', sutra_dossier.id),
                ('name', '=', line.facture_name)
            ])
            if existing_facture:
                line.status = 'error'
                line.error_msg = 'Facture existante dans ce dossier.'
                continue
            
            # Create Invoice
            self.env['sutra.facture'].create({
                'sutra_id': sutra_dossier.id,
                'name': line.facture_name,
                'date': line.date,
                'amount': line.amount,
                'state': 'non_paye'
            })
            
            line.status = 'done'
            line.error_msg = ''
            factures_creees += 1

        if self.valid_lines == 0 and self.error_lines == 0:
            self.state = 'done'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Traitement termine',
                'message': f"{factures_creees} factures creees avec succes.",
                'type': 'success',
                'sticky': False,
            }
        }
"""

new_process = """
    def action_process(self):
        self.ensure_one()
        self.action_verify()
        
        lines_to_process = self.line_ids.filtered(lambda l: l.status in ['ready', 'done', 'error'] and l.logistics_id)

        factures_creees = 0
        for line in lines_to_process:
            # Create or get Sutra Dossier
            sutra_dossier = self.env['sutra.dossier'].search([('logistics_id', '=', line.logistics_id.id)], limit=1)
            if not sutra_dossier:
                sutra_dossier = self.env['sutra.dossier'].create({
                    'logistics_id': line.logistics_id.id,
                })
            
            # Check if invoice exists
            existing_facture = self.env['sutra.facture'].search([
                ('sutra_id', '=', sutra_dossier.id),
                ('name', '=', line.facture_name)
            ])
            if existing_facture:
                line.status = 'done'
                line.error_msg = 'Deja importé'
                continue
            
            # Create Invoice
            self.env['sutra.facture'].create({
                'sutra_id': sutra_dossier.id,
                'name': line.facture_name,
                'date': line.date,
                'amount': line.amount,
                'state': 'non_paye'
            })
            
            line.status = 'done'
            line.error_msg = ''
            factures_creees += 1

        if not self.line_ids.filtered(lambda l: l.status in ['draft', 'error']):
            self.state = 'done'
        else:
            self.state = 'draft'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Traitement termine',
                'message': f"{factures_creees} nouvelles factures creees.",
                'type': 'success',
                'sticky': False,
            }
        }
"""

content = content.replace(old_process.strip(), new_process.strip())

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated python logic")
