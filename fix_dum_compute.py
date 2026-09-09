import os

filepath = 'custom-addons/tanger_med/models/sutra.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_dum = """    @api.depends('logistics_id', 'logistics_id.dum', 'logistics_id.tanger_med_dum')
    def _compute_dum(self):
        for rec in self:
            rec.dum = rec.logistics_id.tanger_med_dum or rec.logistics_id.dum or ''"""

new_dum = """    @api.depends('logistics_id', 'logistics_id.tanger_med_dum')
    def _compute_dum(self):
        for rec in self:
            douane_dum = getattr(rec.logistics_id, 'dum', False)
            rec.dum = rec.logistics_id.tanger_med_dum or douane_dum or ''"""

content = content.replace(old_dum, new_dum)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated dum compute method")
