import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Rename article_id -> legacy_article_id to avoid constraint conflicts on logistique.entry."""
    _logger.info("Achat 1.2 pre-migrate: checking and renaming article_id on logistique_entry")
    
    # Check if column exists before renaming
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'logistique_entry' AND column_name = 'article_id'
    """)
    if cr.fetchone():
        _logger.info("Renaming column article_id to legacy_article_id on logistique_entry")
        cr.execute("""
            ALTER TABLE logistique_entry 
            RENAME COLUMN article_id TO legacy_article_id
        """)
    else:
        _logger.info("Column article_id not found on logistique_entry, skipping rename.")
