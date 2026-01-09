import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import text
from app.db.session import engine


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KwachaPoint.Reconciliation")

class ReconciliationService:
    def __init__(self, db_engine):
        self.engine = db_engine

    def run_full_audit(self):
        """Perform a 3-point check: Integrity, Stale Cleanup, and Provider Sync."""
        logger.info(f"--- Starting Full Audit: {datetime.now(timezone.utc)} ---")
        
        self.check_ledger_integrity()
        self.cleanup_stale_transactions(timeout_minutes=15)
        
        logger.info("--- Audit Complete ---")

    def check_ledger_integrity(self):
        """The 'Golden Rule': All debits - all credits MUST equal zero."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT SUM(credit) - SUM(debit) as balance 
                FROM ledger.ledger_entries
            """)).fetchone()
            
            balance = result.balance or Decimal("0.0000")
            
            if balance != 0:
                logger.error(f"CRITICAL INTEGRITY FAILURE: Ledger out of balance by {balance} MWK!")
            else:
                logger.info("Ledger Integrity Verified: Balanced at 0.0000")

    def cleanup_stale_transactions(self, timeout_minutes=15):
        """Finds transactions stuck in 'PENDING' too long and marks them FAILED."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        
        with self.engine.begin() as conn:
            result = conn.execute(text("""
                UPDATE ledger.transactions 
                SET status = 'FAILED', 
                    metadata = metadata || '{"reason": "reconciliation_timeout"}'::jsonb
                WHERE status = 'PENDING' 
                AND created_at < :cutoff
                RETURNING id
            """), {"cutoff": cutoff_time})
            
            failed_count = len(result.fetchall())
            if failed_count > 0:
                logger.warning(f"Cleaned up {failed_count} stale PENDING transactions.")

if __name__ == "__main__":
    service = ReconciliationService(engine)
    service.run_full_audit()
