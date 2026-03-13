import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Rename article_id -> legacy_article_id on all affected tables."""
    _logger.info("Achat 1.3 pre-migrate: cleaning up article_id constraints")
    
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
        
        # Check if 'legacy_article_id' exists
        cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s AND column_name = 'legacy_article_id'
        """, (table,))
        has_legacy_id = cr.fetchone()
        
        if has_article_id:
            if has_legacy_id:
                _logger.info("Both article_id and legacy_article_id exist in %s. Dropping new column to rename old one.", table)
                # Drop the newly created (likely empty) column to allow renaming the old data-filled one
                cr.execute(f"ALTER TABLE {table} DROP COLUMN legacy_article_id")
            
            _logger.info("Renaming column article_id to legacy_article_id on %s", table)
            cr.execute(f"ALTER TABLE {table} RENAME COLUMN article_id TO legacy_article_id")
        else:
            _logger.info("Column article_id not found on %s, skipping.", table)
