# Cleanup Script for Logistique Synchronization
# Run this in Odoo Shell: python odoo-bin shell -d <db_name>

entries = env['logistique.entry'].search([])
dossiers = env['logistique.dossier'].search([])

print(f"Checking {len(entries)} entries and {len(dossiers)} dossiers...")

# 1. Sync entries that have a bl_number but wrong or missing dossier_id
for entry in entries:
    if entry.bl_number:
        # Check if dossier with this name exists
        dossier = env['logistique.dossier'].search([('name', '=', entry.bl_number)], limit=1)
        
        if not dossier:
            print(f"Creating missing dossier for BL: {entry.bl_number}")
            dossier = env['logistique.dossier'].create({'name': entry.bl_number})
        
        if entry.dossier_id != dossier:
            print(f"Fixing Entry {entry.id}: linking to Dossier {dossier.name} (was {entry.dossier_id.name if entry.dossier_id else 'None'})")
            entry.dossier_id = dossier

# 2. Sync containers to their entry's dossier
containers = env['logistique.container'].search([])
for container in containers:
    if container.entry_id and container.entry_id.dossier_id:
        if container.dossier_id != container.entry_id.dossier_id:
            print(f"Fixing Container {container.name}: linking to Dossier {container.entry_id.dossier_id.name}")
            container.dossier_id = container.entry_id.dossier_id

# 3. Optional: Cleanup dossiers with no entries (be careful if and only if they are not used by Finance)
for dossier in dossiers:
    entry_count = env['logistique.entry'].search_count([('dossier_id', '=', dossier.id)])
    if entry_count == 0:
        # Check if it has finance data before deleting
        has_checks = env['logistique.dossier.cheque'].search_count([('dossier_id', '=', dossier.id)])
        if has_checks == 0:
            print(f"Deleting empty/unused dossier: {dossier.name}")
            # dossier.unlink() # Uncomment if you want to delete them

env.cr.commit()
print("Cleanup finished.")
