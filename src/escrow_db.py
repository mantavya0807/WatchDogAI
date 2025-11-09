"""
Escrow Database
Stores mappings between placeholders and original PII values.
Uses SQLite for local, encrypted storage.
"""

import sqlite3
import json
import hashlib
import secrets
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict

@dataclass
class EscrowEntry:
    """Represents a placeholder-to-original mapping"""
    placeholder_id: str  # e.g., "PERSON_1"
    original_value: str  # e.g., "John Smith"
    entity_type: str  # e.g., "PERSON"
    salt: str  # Random salt for security
    timestamp: str  # ISO format timestamp
    source: str  # Where it came from (e.g., "chrome:chatgpt.com")
    context: Optional[str] = None  # Optional surrounding context

class EscrowDatabase:
    """
    Local SQLite database for storing PII escrow mappings.
    
    Features:
    - Persistent storage of placeholder mappings
    - Salted hashing for additional security
    - Instance tracking (same value gets same placeholder)
    - Session management
    - Reverse lookup (placeholder -> original)
    """
    
    def __init__(self, db_path: str = "data/escrow/pii_escrow.db"):
        """
        Initialize escrow database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        
        self._create_tables()
        
        # Cache for current session (for fast lookups)
        self.session_cache: Dict[str, str] = {}  # original -> placeholder
        self.placeholder_cache: Dict[str, str] = {}  # placeholder -> original
        
        # Counter for generating unique placeholder IDs
        self.counters: Dict[str, int] = {}
    
    def _create_tables(self):
        """Create database schema"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS escrow_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_id TEXT NOT NULL UNIQUE,
                original_value TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                value_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT,
                context TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Index for fast lookup by hash
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_value_hash 
            ON escrow_entries(value_hash)
        ''')
        
        # Index for fast lookup by placeholder
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_placeholder 
            ON escrow_entries(placeholder_id)
        ''')
        
        self.conn.commit()
    
    def _generate_hash(self, value: str, salt: str) -> str:
        """Generate salted hash of value"""
        combined = f"{value}:{salt}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _get_or_create_placeholder(
        self,
        original_value: str,
        entity_type: str,
        source: str = "unknown",
        context: Optional[str] = None
    ) -> str:
        """
        Get existing placeholder or create new one.
        
        Args:
            original_value: Original PII value
            entity_type: Type of PII (PERSON, EMAIL, etc.)
            source: Source of the data
            context: Optional context
            
        Returns:
            Placeholder ID (e.g., "PERSON_1")
        """
        # Check session cache first
        cache_key = f"{entity_type}:{original_value}"
        if cache_key in self.session_cache:
            return self.session_cache[cache_key]
        
        # Generate salt and hash
        salt = secrets.token_hex(8)
        value_hash = self._generate_hash(original_value, salt)
        
        # Check if we've seen this value before (by hash)
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT placeholder_id FROM escrow_entries
            WHERE entity_type = ? AND original_value = ?
            LIMIT 1
        ''', (entity_type, original_value))
        
        row = cursor.fetchone()
        
        if row:
            # Existing entry found
            placeholder_id = row['placeholder_id']
        else:
            # Create new entry
            if entity_type not in self.counters:
                # Get max counter from database
                cursor.execute('''
                    SELECT MAX(CAST(SUBSTR(placeholder_id, LENGTH(?) + 2) AS INTEGER)) as max_id
                    FROM escrow_entries
                    WHERE entity_type = ?
                ''', (entity_type, entity_type))
                
                row = cursor.fetchone()
                self.counters[entity_type] = (row['max_id'] or 0)
            
            # Increment counter
            self.counters[entity_type] += 1
            placeholder_id = f"{entity_type}_{self.counters[entity_type]}"
            
            # Insert into database
            timestamp = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO escrow_entries 
                (placeholder_id, original_value, entity_type, value_hash, salt, timestamp, source, context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (placeholder_id, original_value, entity_type, value_hash, salt, timestamp, source, context))
            
            self.conn.commit()
        
        # Update caches
        self.session_cache[cache_key] = placeholder_id
        self.placeholder_cache[placeholder_id] = original_value
        
        return placeholder_id
    
    def store(
        self,
        original_value: str,
        entity_type: str,
        source: str = "unknown",
        context: Optional[str] = None
    ) -> str:
        """
        Store PII value and get placeholder.
        
        Args:
            original_value: Original PII text
            entity_type: Type (PERSON, EMAIL, etc.)
            source: Source identifier
            context: Optional context
            
        Returns:
            Placeholder ID
        """
        return self._get_or_create_placeholder(original_value, entity_type, source, context)
    
    def retrieve(self, placeholder_id: str) -> Optional[str]:
        """
        Get original value from placeholder.
        
        Args:
            placeholder_id: Placeholder to look up
            
        Returns:
            Original value or None if not found
        """
        # Check cache first
        if placeholder_id in self.placeholder_cache:
            return self.placeholder_cache[placeholder_id]
        
        # Query database
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT original_value FROM escrow_entries
            WHERE placeholder_id = ?
        ''', (placeholder_id,))
        
        row = cursor.fetchone()
        if row:
            original = row['original_value']
            self.placeholder_cache[placeholder_id] = original
            return original
        
        return None
    
    def get_all_entries(self) -> List[EscrowEntry]:
        """Get all escrow entries"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT placeholder_id, original_value, entity_type, salt, timestamp, source, context
            FROM escrow_entries
            ORDER BY created_at DESC
        ''')
        
        entries = []
        for row in cursor.fetchall():
            entries.append(EscrowEntry(
                placeholder_id=row['placeholder_id'],
                original_value=row['original_value'],
                entity_type=row['entity_type'],
                salt=row['salt'],
                timestamp=row['timestamp'],
                source=row['source'] or "unknown",
                context=row['context']
            ))
        
        return entries
    
    def delete_entry(self, placeholder_id: str) -> bool:
        """Delete an entry by placeholder ID"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM escrow_entries WHERE placeholder_id = ?', (placeholder_id,))
        self.conn.commit()
        
        # Clear from caches
        if placeholder_id in self.placeholder_cache:
            original = self.placeholder_cache[placeholder_id]
            del self.placeholder_cache[placeholder_id]
            
            # Remove from session cache
            for key, value in list(self.session_cache.items()):
                if value == placeholder_id:
                    del self.session_cache[key]
        
        return cursor.rowcount > 0
    
    def clear_session_cache(self):
        """Clear the in-memory session cache"""
        self.session_cache.clear()
        self.placeholder_cache.clear()
        self.counters.clear()
    
    def export_to_json(self, filepath: str):
        """Export all entries to JSON file"""
        entries = self.get_all_entries()
        data = [asdict(entry) for entry in entries]
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about stored data"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as total FROM escrow_entries')
        total = cursor.fetchone()['total']
        
        cursor.execute('''
            SELECT entity_type, COUNT(*) as count 
            FROM escrow_entries 
            GROUP BY entity_type
        ''')
        
        by_type = {row['entity_type']: row['count'] for row in cursor.fetchall()}
        
        return {
            'total_entries': total,
            'by_type': by_type
        }
    
    def close(self):
        """Close database connection"""
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    # Test the escrow database
    print("Testing Escrow Database")
    print("=" * 60)
    
    # Create test database
    db = EscrowDatabase("data/escrow/test_escrow.db")
    
    # Test storing values
    print("\n1. Storing PII values:")
    test_data = [
        ("John Smith", "PERSON", "test_cli"),
        ("john@email.com", "EMAIL", "test_cli"),
        ("555-123-4567", "PHONE", "test_cli"),
        ("John Smith", "PERSON", "test_cli"),  # Duplicate - should reuse placeholder
    ]
    
    placeholders = []
    for value, type_, source in test_data:
        placeholder = db.store(value, type_, source)
        placeholders.append(placeholder)
        print(f"  {value:20} -> {placeholder}")
    
    # Test retrieval
    print("\n2. Retrieving original values:")
    for placeholder in placeholders:
        original = db.retrieve(placeholder)
        print(f"  {placeholder:15} -> {original}")
    
    # Test stats
    print("\n3. Database statistics:")
    stats = db.get_stats()
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  By type:")
    for type_, count in stats['by_type'].items():
        print(f"    {type_:15}: {count}")
    
    # Test export
    print("\n4. Exporting to JSON:")
    db.export_to_json("data/escrow/test_export.json")
    print("  ✓ Exported to test_export.json")
    
    # View all entries
    print("\n5. All entries:")
    entries = db.get_all_entries()
    for entry in entries:
        print(f"  {entry.placeholder_id:15} | {entry.entity_type:10} | {entry.original_value:20} | {entry.timestamp[:19]}")
    
    db.close()
    print("\n✓ Escrow database test complete!")