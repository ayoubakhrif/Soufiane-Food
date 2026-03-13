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
        # Check if column exists before renaming
        cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s AND column_name = 'article_id'
        """, (table,))
        
        if cr.fetchone():
            _logger.info("Renaming column article_id to legacy_article_id on %s", table)
            cr.execute(f"ALTER TABLE {table} RENAME COLUMN article_id TO legacy_article_id")
        else:
            _logger.info("Column article_id not found on %s, skipping.", table)
