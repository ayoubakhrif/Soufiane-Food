import os

filepath = 'custom-addons/tanger_med/models/sutra_import_batch.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update status selection
content = content.replace(
    "('error', 'Erreur'),",
    "('error', 'Erreur'),\n        ('orphan', 'Orpheline'),"
)

# 2. Update stats compute
content = content.replace(
    "rec.valid_lines = len(rec.line_ids.filtered(lambda l: l.status == 'ready'))",
    "rec.valid_lines = len(rec.line_ids.filtered(lambda l: l.status in ['ready', 'orphan']))"
)

# 3. Update verify loop
content = content.replace(
    "['draft', 'error']",
    "['draft', 'error', 'orphan']"
)

# 4. Update _check_dum logic
old_check_dum = """            clean_dum = rec.dum.lstrip('0')
            
            domain = [('tanger_med_dum', 'ilike', clean_dum)] if clean_dum else []
            entry = self.env['logistique.entry'].search(domain, limit=1)
            if entry:
                rec.logistics_id = entry.id
                rec.status = 'ready'
                rec.error_msg = ''
            else:
                rec.logistics_id = False
                rec.status = 'error'
                rec.error_msg = 'DUM introuvable'"""

new_check_dum = """            clean_dum = str(rec.dum).strip().upper()
            
            # Allow matching ignoring leading zeros if needed, but strict upper is better
            # Try exact match first
            entry = self.env['logistique.entry'].search([('tanger_med_dum', '=ilike', clean_dum)], limit=1)
            
            if not entry and clean_dum.lstrip('0'):
                entry = self.env['logistique.entry'].search([('tanger_med_dum', '=ilike', clean_dum.lstrip('0'))], limit=1)
            
            if entry:
                rec.logistics_id = entry.id
                rec.status = 'ready'
                rec.error_msg = ''
            else:
                rec.logistics_id = False
                rec.status = 'orphan'
                rec.error_msg = 'DUM introuvable - Sera enregistrée comme Orpheline'"""

content = content.replace(old_check_dum, new_check_dum)

# 5. Update action_process logic
old_process = """        lines_to_process = self.line_ids.filtered(lambda l: l.status in ['ready', 'done', 'error'] and l.logistics_id)

        factures_creees = 0
        for line in lines_to_process:
            if not line.logistics_id:
                continue
                
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
            factures_creees += 1"""

new_process = """        lines_to_process = self.line_ids.filtered(lambda l: l.status in ['ready', 'orphan'])

        factures_creees = 0
        for line in lines_to_process:
            sutra_dossier = False
            
            if line.logistics_id:
                sutra_dossier = self.env['sutra.dossier'].search([('logistics_id', '=', line.logistics_id.id)], limit=1)
                if not sutra_dossier:
                    sutra_dossier = self.env['sutra.dossier'].create({
                        'logistics_id': line.logistics_id.id,
                    })
            
            # Check if invoice exists
            if sutra_dossier:
                existing_facture = self.env['sutra.facture'].search([
                    ('sutra_id', '=', sutra_dossier.id),
                    ('name', '=', line.facture_name)
                ])
                if existing_facture:
                    line.status = 'done'
                    line.error_msg = 'Deja importé'
                    continue
            else:
                existing_orphan = self.env['sutra.facture'].search([
                    ('sutra_id', '=', False),
                    ('name', '=', line.facture_name)
                ])
                if existing_orphan:
                    line.status = 'done'
                    line.error_msg = 'Deja importé (Orpheline)'
                    continue
            
            # Create Invoice
            vals = {
                'name': line.facture_name,
                'date': line.date,
                'amount': line.amount,
                'state': 'non_paye'
            }
            if sutra_dossier:
                vals['sutra_id'] = sutra_dossier.id
            else:
                vals['dum_provisoire'] = str(line.dum).strip().upper() if line.dum else ''
                
            self.env['sutra.facture'].create(vals)
            
            line.status = 'done'
            line.error_msg = ''
            factures_creees += 1"""

content = content.replace(old_process, new_process)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sutra_import_batch.py")
