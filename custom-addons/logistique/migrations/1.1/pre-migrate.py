# -*- coding: utf-8 -*-
"""
Migration 1.0 -> 1.1: container_ids removed from logistique.dossier

Changes:
- logistique.dossier no longer has a direct container_ids One2many.
  Containers are now linked via logistique.entry (entry_id FK on logistique.container).
- fret_amount stored computed field added to logistique.dossier.
- container_count now counts via entry_ids.container_ids.

Migration steps:
1. For each logistique.container that has a dossier_id but NO entry_id:
   - Find the logistique.entry that belongs to that dossier (first one if multiple).
   - Set entry_id on the container to link it properly.
2. Recompute container_count and fret_amount on all dossiers.
"""


def migrate(cr, version):
    if not version:
        return

    # Step 1: Populate entry_id on containers that only have dossier_id
    cr.execute("""
        UPDATE logistique_container lc
        SET entry_id = (
            SELECT le.id
            FROM logistique_entry le
            WHERE le.dossier_id = lc.dossier_id
            ORDER BY le.id
            LIMIT 1
        )
        WHERE lc.dossier_id IS NOT NULL
          AND lc.entry_id IS NULL
    """)

    rows_updated = cr.rowcount
    if rows_updated:
        print(f"[Migration 1.1] Linked {rows_updated} container(s) to their logistique.entry.")
    else:
        print("[Migration 1.1] No containers needed entry_id update.")

    # Step 2: Reset container_count on dossiers so Odoo recomputes on upgrade
    cr.execute("""
        UPDATE logistique_dossier
        SET container_count = (
            SELECT COUNT(*)
            FROM logistique_container lc2
            JOIN logistique_entry le2 ON lc2.entry_id = le2.id
            WHERE le2.dossier_id = logistique_dossier.id
        )
    """)
    print("[Migration 1.1] Recomputed container_count on all dossiers.")

    # Step 4: Recompute container_count on entries (now entry-level, not dossier-level)
    cr.execute("""
        UPDATE logistique_entry le
        SET container_count = (
            SELECT COUNT(*)
            FROM logistique_container lc
            WHERE lc.entry_id = le.id
        )
    """)
    print("[Migration 1.1] Recomputed container_count on all entries.")

    # Step 3: Reset fret_amount to 0 so it gets recomputed by Odoo
    cr.execute("""
        UPDATE logistique_dossier SET fret_amount = 0
    """)
    print("[Migration 1.1] Reset fret_amount on all dossiers (will be recomputed).")
