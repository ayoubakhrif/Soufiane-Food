import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Rename article_id -> legacy_article_id to preserve logistique.article data."""
    _logger.info("Achat 1.1 pre-migrate: renaming article_id -> legacy_article_id on achat_contract")
    cr.execute("""
        ALTER TABLE achat_contract
        RENAME COLUMN article_id TO legacy_article_id
    """)
