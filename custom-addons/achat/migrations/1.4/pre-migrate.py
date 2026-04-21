import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """
    Forcefully resolve the article_id conflict.
    Rename column: article_id -> achat_article_id
    Odoo will then recreate article_id from the base logistique module.
    """
    _logger.info("Achat 1.4 pre-migrate: resolving article_id conflict")
    
    tables_to_check = [
        'logistique_entry',
        'claims_dhl_delay',
        'claims_divers',
        'claims_franchise_difference',
        'claims_quality',
        'claims_quantity'
    ]

    for table in tables_to_check:
        # Check if 'article_id' exists
        cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s AND column_name = 'article_id'
        """, (table,))
        has_article_id = cr.fetchone()
        
        # Check if 'achat_article_id' exists
        cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s AND column_name = 'achat_article_id'
        """, (table,))
        has_achat_id = cr.fetchone()
        
        if has_article_id:
            if not has_achat_id:
                _logger.info("Renaming column article_id to achat_article_id on %s", table)
                # This moves the OLD data (achat.article IDs) to the NEW field name
                cr.execute(f"ALTER TABLE {table} RENAME COLUMN article_id TO achat_article_id")
            else:
                _logger.info("Both article_id and achat_article_id exist on %s. Clearing article_id content.", table)
                # If both exist, we clear article_id so Odoo can drop/recreate the constraint without data errors
                cr.execute(f"UPDATE {table} SET article_id = NULL")
                # We drop the constraint manually to be sure
                constraint_name = f"{table}_article_id_fkey"
                cr.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint_name} CASCADE")
        else:
            _logger.info("Column article_id not found on %s, skipping.", table)

    # Note: Odoo will automatically add back 'article_id' pointing to logistique.article
    # because it's defined in the 'logistique' module and no longer overridden in 'achat'.
