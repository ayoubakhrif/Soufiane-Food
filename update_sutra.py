import os

filepath = 'custom-addons/tanger_med/models/sutra.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Make sutra_id optional
content = content.replace(
    "sutra_id = fields.Many2one('sutra.dossier', string='Dossier SUTRA', ondelete='cascade', required=True)",
    "sutra_id = fields.Many2one('sutra.dossier', string='Dossier SUTRA', ondelete='cascade', required=False)\n    dum_provisoire = fields.Char(string='DUM Provisoire (Orpheline)')"
)

# Modify SutraDossier to auto-link orphans
old_compute_dum = """    @api.depends('logistics_id', 'logistics_id.tanger_med_dum')
    def _compute_dum(self):
        for rec in self:
            douane_dum = getattr(rec.logistics_id, 'dum', False)
            rec.dum = rec.logistics_id.tanger_med_dum or douane_dum or ''"""

new_compute_dum = """    @api.depends('logistics_id', 'logistics_id.tanger_med_dum')
    def _compute_dum(self):
        for rec in self:
            douane_dum = getattr(rec.logistics_id, 'dum', False)
            rec.dum = rec.logistics_id.tanger_med_dum or douane_dum or ''
            
            # Auto-link orphans
            if rec.dum:
                clean_dum = str(rec.dum).strip().upper()
                orphans = self.env['sutra.facture'].search([('sutra_id', '=', False), ('dum_provisoire', '!=', False)])
                for orphan in orphans:
                    if orphan.dum_provisoire and orphan.dum_provisoire.strip().upper() == clean_dum:
                        orphan.sutra_id = rec.id
                        orphan.dum_provisoire = False"""

content = content.replace(old_compute_dum, new_compute_dum)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sutra.py")
