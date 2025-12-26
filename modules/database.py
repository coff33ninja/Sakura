"""
Database Module for Sakura
Async SQLite wrapper with connection pooling and CRUD operations

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiosqlite for async database operations
"""
import asyncio
import logging
import json
import os
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
from pathlib import Path

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False
    logging.warning("aiosqlite not installed - database features disabled. Install with: pip install aiosqlite")


class DatabaseManager:
    """Async SQLite database manager for Sakura's memory system"""
    
    def __init__(self, db_path: Union[str, Path] = None):
        # Allow environment variable override, fallback to parameter, then default
        if db_path is None:
            db_path = os.getenv("DB_PATH", "sakura.db")
        
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self._lock = asyncio.Lock()
        self._connection: Optional['aiosqlite.Connection'] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize database connection and create schema"""
        if not HAS_AIOSQLITE:
            logging.error("aiosqlite not available - database disabled")
            return False
        
        async with self._lock:
            try:
                # Ensure parent directory exists
                if self.db_path.parent != Path('.'):
                    self.db_path.parent.mkdir(parents=True, exist_ok=True)
                
                self._connection = await aiosqlite.connect(str(self.db_path))
                self._connection.row_factory = aiosqlite.Row
                
                # Enable foreign keys and WAL mode for better concurrency
                await self._connection.execute("PRAGMA foreign_keys = ON")
                await self._connection.execute("PRAGMA journal_mode = WAL")
                
                # Create schema
                await self._create_schema()
                
                self._initialized = True
                logging.info(f"Database initialized: {self.db_path}")
                return True
            except Exception as e:
                logging.error(f"Failed to initialize database: {e}")
                return False
    
    async def _create_schema(self):
        """Create database tables if they don't exist"""
        schema = '''
        -- Subjects: High-level categories/topics
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Events: Things that happened (conversations, discoveries, errors)
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
            event_type TEXT NOT NULL,
            title TEXT,
            description TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Tasks: Things to do or that were done
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,
            parent_task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
            status TEXT DEFAULT 'pending',
            title TEXT NOT NULL,
            description TEXT,
            priority INTEGER DEFAULT 0,
            due_date TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Actions: Tool executions
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
            tool_name TEXT NOT NULL,
            action_name TEXT NOT NULL,
            parameters TEXT,
            result TEXT,
            status TEXT,
            error_message TEXT,
            duration_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- User Info: Key-value store for user data
        CREATE TABLE IF NOT EXISTS user_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Facts: Things Sakura knows
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT,
            source TEXT DEFAULT 'user_stated',
            confidence REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Discovered Locations: Paths Sakura has found
        CREATE TABLE IF NOT EXISTS discovered_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_type TEXT,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            verified INTEGER DEFAULT 1,
            last_verified TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, path)
        );
        
        -- Scripts: Scripts Sakura has created
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            script_type TEXT,
            description TEXT,
            content_hash TEXT,
            last_executed TIMESTAMP,
            execution_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Conversations: Conversation summaries
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            summary TEXT,
            topics TEXT,
            mood TEXT,
            exchange_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Topics: Discussed topics with frequency
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            mention_count INTEGER DEFAULT 1,
            first_mentioned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_mentioned TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Important Dates
        CREATE TABLE IF NOT EXISTS important_dates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            date_value TEXT NOT NULL,
            description TEXT,
            recurring INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Session Stats
        CREATE TABLE IF NOT EXISTS session_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            action_count INTEGER DEFAULT 0,
            tool_usage TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- User Feedback/Reactions: Track user corrections and preferences
        CREATE TABLE IF NOT EXISTS user_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id INTEGER REFERENCES actions(id) ON DELETE SET NULL,
            feedback_type TEXT NOT NULL,  -- 'correction', 'positive', 'negative', 'preference'
            user_message TEXT,            -- What user said ("no, I meant...", "don't do that")
            original_action TEXT,         -- What Sakura did wrong
            correct_action TEXT,          -- What user wanted instead
            context TEXT,                 -- JSON: surrounding context
            applied INTEGER DEFAULT 0,    -- Whether this feedback has been learned
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Learned Corrections: Patterns Sakura should remember
        CREATE TABLE IF NOT EXISTS learned_corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger_pattern TEXT NOT NULL,    -- What triggers this correction (regex or keywords)
            wrong_behavior TEXT,              -- What NOT to do
            correct_behavior TEXT NOT NULL,   -- What TO do instead
            tool_name TEXT,                   -- Specific tool this applies to
            action_name TEXT,                 -- Specific action this applies to
            confidence REAL DEFAULT 1.0,      -- How confident (based on repetition)
            use_count INTEGER DEFAULT 0,      -- How many times this was applied
            session_id TEXT,                  -- NULL = permanent, otherwise session-specific
            is_permanent INTEGER DEFAULT 1,   -- 1 = permanent, 0 = session-only
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Conversation Exchanges: Full conversation history (infinite)
        CREATE TABLE IF NOT EXISTS conversation_exchanges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_input TEXT,
            ai_response TEXT,
            tools_used TEXT,          -- JSON array of tools
            tool_results TEXT,        -- JSON array of results
            mood TEXT,
            topics TEXT,              -- JSON array of topics
            user_feedback_id INTEGER REFERENCES user_feedback(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Action History: Extended action log (infinite, no limit)
        -- Note: 'actions' table already exists, but we remove the limit
        -- and add more context fields
        
        -- Tool Usage Patterns: Track how tools are used for optimization
        CREATE TABLE IF NOT EXISTS tool_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT NOT NULL,
            action_name TEXT NOT NULL,
            common_params TEXT,           -- JSON: most common parameter combinations
            success_rate REAL DEFAULT 1.0,
            avg_duration_ms INTEGER,
            total_uses INTEGER DEFAULT 1,
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tool_name, action_name)
        );
        
        -- Error Patterns: Track errors to avoid repeating them
        CREATE TABLE IF NOT EXISTS error_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT,
            action_name TEXT,
            error_type TEXT NOT NULL,     -- 'not_found', 'permission', 'timeout', etc.
            error_message TEXT,
            context TEXT,                 -- JSON: what was happening
            solution TEXT,                -- What fixed it (if known)
            occurrence_count INTEGER DEFAULT 1,
            last_occurred TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Notes: Quick notes with FTS search support
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT UNIQUE NOT NULL,  -- External ID like 'note_1_123456'
            title TEXT NOT NULL,
            content TEXT,
            tags TEXT,                     -- JSON array of tags
            pinned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Todos: Task tracking with history
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            todo_id TEXT UNIQUE NOT NULL,  -- External ID like 'todo_1_123456'
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT DEFAULT 'medium',  -- low, medium, high, urgent
            due_date TIMESTAMP,
            completed INTEGER DEFAULT 0,
            completed_at TIMESTAMP,
            tags TEXT,                     -- JSON array of tags
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Connection Profiles: SSH, SMB, FTP, RDP, etc.
        CREATE TABLE IF NOT EXISTS connection_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT UNIQUE NOT NULL,   -- External ID like 'ssh_1_123456'
            profile_type TEXT NOT NULL,        -- ssh, smb, ftp, sftp, rdp
            name TEXT NOT NULL,                -- User-friendly name
            host TEXT NOT NULL,
            port INTEGER,
            username TEXT,
            auth_type TEXT DEFAULT 'password', -- password, key, ntlm, kerberos
            key_path TEXT,                     -- Path to SSH key or certificate
            domain TEXT,                       -- For SMB/RDP Windows domain
            share_path TEXT,                   -- For SMB share path
            remote_path TEXT,                  -- Default remote directory
            local_path TEXT,                   -- Default local directory for transfers
            use_ssl INTEGER DEFAULT 0,         -- For FTP -> FTPS
            passive_mode INTEGER DEFAULT 1,    -- For FTP passive mode
            extra_config TEXT,                 -- JSON for type-specific options
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            use_count INTEGER DEFAULT 0
        );
        
        -- Extension Scripts: AI-generated scripts to extend capabilities
        CREATE TABLE IF NOT EXISTS extension_scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            script_id TEXT UNIQUE NOT NULL,    -- External ID like 'ext_spotify_123456'
            name TEXT NOT NULL,                -- Script name
            description TEXT,                  -- What the script does
            language TEXT NOT NULL,            -- python, powershell, batch, javascript
            code TEXT NOT NULL,                -- The actual script code
            category TEXT,                     -- Capability category (media, automation, etc.)
            trigger_phrases TEXT,              -- JSON array of trigger phrases
            parameters TEXT,                   -- JSON object of expected parameters
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            use_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            is_verified INTEGER DEFAULT 0      -- User verified as working
        );
        
        -- Create indexes for common queries
        CREATE INDEX IF NOT EXISTS idx_events_subject ON events(subject_id);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_task_id);
        CREATE INDEX IF NOT EXISTS idx_actions_tool ON actions(tool_name);
        CREATE INDEX IF NOT EXISTS idx_actions_created ON actions(created_at);
        CREATE INDEX IF NOT EXISTS idx_locations_type ON discovered_locations(location_type);
        CREATE INDEX IF NOT EXISTS idx_locations_name ON discovered_locations(name);
        CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
        
        -- Indexes for new tables
        CREATE INDEX IF NOT EXISTS idx_feedback_type ON user_feedback(feedback_type);
        CREATE INDEX IF NOT EXISTS idx_feedback_action ON user_feedback(action_id);
        CREATE INDEX IF NOT EXISTS idx_feedback_created ON user_feedback(created_at);
        CREATE INDEX IF NOT EXISTS idx_corrections_tool ON learned_corrections(tool_name);
        CREATE INDEX IF NOT EXISTS idx_corrections_trigger ON learned_corrections(trigger_pattern);
        CREATE INDEX IF NOT EXISTS idx_exchanges_session ON conversation_exchanges(session_id);
        CREATE INDEX IF NOT EXISTS idx_exchanges_created ON conversation_exchanges(created_at);
        CREATE INDEX IF NOT EXISTS idx_tool_patterns_tool ON tool_patterns(tool_name, action_name);
        CREATE INDEX IF NOT EXISTS idx_error_patterns_tool ON error_patterns(tool_name, action_name);
        CREATE INDEX IF NOT EXISTS idx_error_patterns_type ON error_patterns(error_type);
        CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title);
        CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned);
        CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at);
        CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(completed);
        CREATE INDEX IF NOT EXISTS idx_todos_priority ON todos(priority);
        CREATE INDEX IF NOT EXISTS idx_todos_due_date ON todos(due_date);
        CREATE INDEX IF NOT EXISTS idx_todos_created ON todos(created_at);
        CREATE INDEX IF NOT EXISTS idx_conn_profiles_type ON connection_profiles(profile_type);
        CREATE INDEX IF NOT EXISTS idx_conn_profiles_host ON connection_profiles(host);
        CREATE INDEX IF NOT EXISTS idx_conn_profiles_last_used ON connection_profiles(last_used);
        CREATE INDEX IF NOT EXISTS idx_ext_scripts_name ON extension_scripts(name);
        CREATE INDEX IF NOT EXISTS idx_ext_scripts_category ON extension_scripts(category);
        CREATE INDEX IF NOT EXISTS idx_ext_scripts_language ON extension_scripts(language);
        CREATE INDEX IF NOT EXISTS idx_ext_scripts_verified ON extension_scripts(is_verified);
        
        -- FTS5 Full-Text Search virtual table for fast searching
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
            content,
            source,
            source_id UNINDEXED,
            tokenize='porter unicode61'
        );
        '''
        
        # Execute schema creation
        await self._connection.executescript(schema)
        await self._connection.commit()
        
        # Populate FTS if empty
        await self._populate_fts()
    
    # ==================== Security Validation ====================
    
    def _is_valid_table_name(self, table: str) -> bool:
        """
        Validate table name to prevent SQL injection attacks.
        Only allows alphanumeric characters and underscores.
        
        Args:
            table: Table name to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(table, str) or not table:
            return False
        
        # List of allowed table names (whitelist approach)
        allowed_tables = {
            'subjects', 'events', 'tasks', 'reminders', 'todos', 'notes',
            'connections', 'actions', 'user_feedback', 'learned_corrections',
            'conversation_exchanges', 'action_history', 'memory_items',
            'conversation_context', 'error_patterns', 'user_info',
            'tool_usage', 'connection_profiles', 'extension_scripts',
            'fts_memory', 'conversation_exchanges_fts', 'event_search',
            'memory_full_text'
        }
        
        return table.lower() in allowed_tables
    
    # ==================== CRUD Operations ====================
    
    async def insert(self, table: str, data: Dict[str, Any]) -> int:
        """Insert a row and return the ID"""
        if not self._initialized:
            return -1
        
        async with self._lock:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            values = list(data.values())
            
            # Convert dicts/lists to JSON strings
            values = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in values]
            
            # Validate table name to prevent SQL injection
            if not self._is_valid_table_name(table):
                logging.error(f"Invalid table name: {table}")
                return -1
            
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            try:
                cursor = await self._connection.execute(query, values)
                await self._connection.commit()
                row_id = cursor.lastrowid
                
                # Auto-index in FTS for searchable tables
                await self._auto_index_fts(table, data, row_id)
                
                return row_id
            except Exception as e:
                logging.error(f"Insert error in {table}: {e}")
                return -1
    
    async def _auto_index_fts(self, table: str, data: Dict[str, Any], row_id: int):
        """Automatically index content in FTS based on table"""
        try:
            content = None
            source = None
            
            if table == "facts":
                content = data.get("content", "")
                source = "fact"
            elif table == "user_info":
                content = f"{data.get('key', '')}: {data.get('value', '')}"
                source = "user_info"
            elif table == "conversations":
                content = f"{data.get('summary', '')} {data.get('topics', '')}"
                source = "conversation"
            elif table == "scripts":
                content = f"{data.get('name', '')} {data.get('description', '')}"
                source = "script"
            elif table == "discovered_locations":
                content = f"{data.get('name', '')} {data.get('path', '')}"
                source = "location"
            elif table == "conversation_exchanges":
                content = f"{data.get('user_input', '')} {data.get('ai_response', '')}"
                source = "exchange"
            
            if content and source:
                await self._add_to_fts(content, source, row_id)
                await self._connection.commit()
        except Exception as e:
            logging.debug(f"FTS auto-index error: {e}")
    
    async def update(self, table: str, data: Dict[str, Any], where: str, where_params: Tuple = ()) -> bool:
        """Update rows matching condition"""
        if not self._initialized:
            return False
        
        async with self._lock:
            # Validate table name to prevent SQL injection
            if not self._is_valid_table_name(table):
                logging.error(f"Invalid table name: {table}")
                return False
            
            set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
            values = list(data.values())
            values = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in values]
            values.extend(where_params)
            
            query = f"UPDATE {table} SET {set_clause} WHERE {where}"
            
            try:
                await self._connection.execute(query, values)
                await self._connection.commit()
                return True
            except Exception as e:
                logging.error(f"Update error in {table}: {e}")
                return False
    
    async def delete(self, table: str, where: str, where_params: Tuple = ()) -> bool:
        """Delete rows matching condition"""
        if not self._initialized:
            return False
        
        async with self._lock:
            # Validate table name to prevent SQL injection
            if not self._is_valid_table_name(table):
                logging.error(f"Invalid table name: {table}")
                return False
            
            query = f"DELETE FROM {table} WHERE {where}"
            
            try:
                await self._connection.execute(query, where_params)
                await self._connection.commit()
                return True
            except Exception as e:
                logging.error(f"Delete error in {table}: {e}")
                return False
    
    async def select(
        self, 
        table: str, 
        columns: str = "*", 
        where: str = None, 
        where_params: Tuple = (),
        order_by: str = None,
        limit: int = None,
        offset: int = None
    ) -> List[Dict[str, Any]]:
        """Select rows from table"""
        if not self._initialized:
            return []
        
        async with self._lock:
            # Validate table name to prevent SQL injection
            if not self._is_valid_table_name(table):
                logging.error(f"Invalid table name: {table}")
                return []
            
            query = f"SELECT {columns} FROM {table}"
            
            if where:
                query += f" WHERE {where}"
            if order_by:
                query += f" ORDER BY {order_by}"
            if limit:
                query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
            
            try:
                cursor = await self._connection.execute(query, where_params)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
            except Exception as e:
                logging.error(f"Select error in {table}: {e}")
                return []
    
    async def select_one(
        self, 
        table: str, 
        columns: str = "*", 
        where: str = None, 
        where_params: Tuple = ()
    ) -> Optional[Dict[str, Any]]:
        """Select single row from table"""
        results = await self.select(table, columns, where, where_params, limit=1)
        return results[0] if results else None
    
    async def execute_raw(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute raw SQL query"""
        if not self._initialized:
            return []
        
        async with self._lock:
            try:
                cursor = await self._connection.execute(query, params)
                if query.strip().upper().startswith("SELECT"):
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
                else:
                    await self._connection.commit()
                    return []
            except Exception as e:
                logging.error(f"Raw query error: {e}")
                return []
    
    async def count(self, table: str, where: str = None, where_params: Tuple = ()) -> int:
        """Count rows in table"""
        if not self._initialized:
            return 0
        
        async with self._lock:
            # Validate table name to prevent SQL injection
            if not self._is_valid_table_name(table):
                logging.error(f"Invalid table name: {table}")
                return 0
            
            query = f"SELECT COUNT(*) as count FROM {table}"
            if where:
                query += f" WHERE {where}"
            
            try:
                cursor = await self._connection.execute(query, where_params)
                row = await cursor.fetchone()
                return row['count'] if row else 0
            except Exception as e:
                logging.error(f"Count error in {table}: {e}")
                return 0
    
    # ==================== Search Operations ====================
    
    async def search_text(
        self, 
        tables: List[str], 
        search_term: str, 
        text_columns: Dict[str, List[str]],
        limit: int = 50
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Search for text across multiple tables"""
        if not self._initialized:
            return {}
        
        results = {}
        search_pattern = f"%{search_term}%"
        
        for table in tables:
            if table not in text_columns:
                continue
            
            columns = text_columns[table]
            where_clauses = [f"{col} LIKE ?" for col in columns]
            where = " OR ".join(where_clauses)
            params = tuple([search_pattern] * len(columns))
            
            table_results = await self.select(
                table, 
                "*", 
                where, 
                params, 
                order_by="created_at DESC",
                limit=limit
            )
            
            if table_results:
                results[table] = table_results
        
        return results
    
    # ==================== FTS5 Full-Text Search ====================
    
    async def _populate_fts(self):
        """Populate FTS index from existing data"""
        if not self._initialized:
            return
        
        try:
            # Check if FTS is already populated
            cursor = await self._connection.execute("SELECT COUNT(*) as count FROM memory_fts")
            row = await cursor.fetchone()
            if row and row['count'] > 0:
                return  # Already populated
            
            # Index facts
            facts = await self.select("facts")
            for fact in facts:
                await self._add_to_fts(fact['content'], 'fact', fact['id'])
            
            # Index user_info
            user_info = await self.select("user_info")
            for info in user_info:
                await self._add_to_fts(f"{info['key']}: {info['value']}", 'user_info', info['id'])
            
            # Index conversations
            convos = await self.select("conversations")
            for conv in convos:
                content = f"{conv.get('summary', '')} {conv.get('topics', '')}"
                await self._add_to_fts(content, 'conversation', conv['id'])
            
            # Index scripts
            scripts = await self.select("scripts")
            for script in scripts:
                content = f"{script['name']} {script.get('description', '')}"
                await self._add_to_fts(content, 'script', script['id'])
            
            # Index discovered_locations
            locations = await self.select("discovered_locations")
            for loc in locations:
                content = f"{loc['name']} {loc['path']}"
                await self._add_to_fts(content, 'location', loc['id'])
            
            # Index conversation_exchanges
            exchanges = await self.select("conversation_exchanges", limit=1000)
            for ex in exchanges:
                content = f"{ex.get('user_input', '')} {ex.get('ai_response', '')}"
                await self._add_to_fts(content, 'exchange', ex['id'])
            
            await self._connection.commit()
            logging.info("FTS index populated")
        except Exception as e:
            logging.warning(f"FTS population error: {e}")
    
    async def _add_to_fts(self, content: str, source: str, source_id: int):
        """Add content to FTS index"""
        if not content or not self._initialized:
            return
        
        try:
            await self._connection.execute(
                "INSERT INTO memory_fts (content, source, source_id) VALUES (?, ?, ?)",
                (content, source, str(source_id))
            )
        except Exception as e:
            logging.debug(f"FTS insert error: {e}")
    
    async def search_fts(self, query: str, limit: int = 50, source_filter: str = None) -> List[Dict[str, Any]]:
        """Fast full-text search using FTS5"""
        if not self._initialized:
            return []
        
        try:
            # Escape special FTS characters and format query
            # FTS5 uses * for prefix matching
            search_query = query.replace('"', '""')
            
            if source_filter:
                sql = """
                    SELECT content, source, source_id, 
                           bm25(memory_fts) as rank
                    FROM memory_fts 
                    WHERE memory_fts MATCH ? AND source = ?
                    ORDER BY rank
                    LIMIT ?
                """
                params = (search_query, source_filter, limit)
            else:
                sql = """
                    SELECT content, source, source_id,
                           bm25(memory_fts) as rank
                    FROM memory_fts 
                    WHERE memory_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """
                params = (search_query, limit)
            
            async with self._lock:
                cursor = await self._connection.execute(sql, params)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logging.warning(f"FTS search error: {e}")
            return []
    
    async def index_content(self, content: str, source: str, source_id: int):
        """Add new content to FTS index (call after insert)"""
        await self._add_to_fts(content, source, source_id)
        try:
            await self._connection.commit()
        except Exception as e:
            logging.debug(f"Failed to commit FTS index: {e}")
    
    # ==================== Specialized Queries ====================
    
    async def get_recent_actions(self, limit: int = 20, tool_name: str = None) -> List[Dict[str, Any]]:
        """Get recent actions, optionally filtered by tool"""
        where = "tool_name = ?" if tool_name else None
        params = (tool_name,) if tool_name else ()
        
        return await self.select(
            "actions",
            "*",
            where,
            params,
            order_by="created_at DESC",
            limit=limit
        )
    
    async def get_task_tree(self, task_id: int) -> Dict[str, Any]:
        """Get a task with all its subtasks recursively"""
        task = await self.select_one("tasks", "*", "id = ?", (task_id,))
        if not task:
            return {}
        
        # Get subtasks
        subtasks = await self.select("tasks", "*", "parent_task_id = ?", (task_id,))
        task['subtasks'] = []
        
        for subtask in subtasks:
            subtask_tree = await self.get_task_tree(subtask['id'])
            task['subtasks'].append(subtask_tree)
        
        # Get actions for this task
        task['actions'] = await self.select("actions", "*", "task_id = ?", (task_id,))
        
        return task
    
    async def get_subject_timeline(self, subject_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chronological events for a subject"""
        return await self.select(
            "events",
            "*",
            "subject_id = ?",
            (subject_id,),
            order_by="created_at DESC",
            limit=limit
        )
    
    async def upsert_topic(self, topic_name: str) -> int:
        """Insert or update topic mention count"""
        existing = await self.select_one("topics", "*", "name = ?", (topic_name.lower(),))
        
        if existing:
            await self.update(
                "topics",
                {
                    "mention_count": existing['mention_count'] + 1,
                    "last_mentioned": datetime.now().isoformat()
                },
                "id = ?",
                (existing['id'],)
            )
            return existing['id']
        else:
            return await self.insert("topics", {
                "name": topic_name.lower(),
                "mention_count": 1,
                "first_mentioned": datetime.now().isoformat(),
                "last_mentioned": datetime.now().isoformat()
            })
    
    async def upsert_location(self, location_type: str, name: str, path: str) -> int:
        """Insert or update discovered location"""
        existing = await self.select_one(
            "discovered_locations", 
            "*", 
            "name = ? AND path = ?", 
            (name, path)
        )
        
        if existing:
            await self.update(
                "discovered_locations",
                {
                    "verified": 1,
                    "last_verified": datetime.now().isoformat()
                },
                "id = ?",
                (existing['id'],)
            )
            return existing['id']
        else:
            return await self.insert("discovered_locations", {
                "location_type": location_type,
                "name": name,
                "path": path,
                "verified": 1,
                "last_verified": datetime.now().isoformat()
            })
    
    # ==================== User Feedback & Learning ====================
    
    async def log_user_feedback(
        self, 
        feedback_type: str, 
        user_message: str, 
        original_action: str = None,
        correct_action: str = None,
        action_id: int = None,
        context: Dict[str, Any] = None
    ) -> int:
        """Log user feedback/correction"""
        return await self.insert("user_feedback", {
            "action_id": action_id,
            "feedback_type": feedback_type,
            "user_message": user_message,
            "original_action": original_action,
            "correct_action": correct_action,
            "context": json.dumps(context) if context else None,
            "applied": 0,
            "created_at": datetime.now().isoformat()
        })
    
    async def add_learned_correction(
        self,
        trigger_pattern: str,
        correct_behavior: str,
        wrong_behavior: str = None,
        tool_name: str = None,
        action_name: str = None,
        session_id: str = None,
        is_permanent: bool = True
    ) -> int:
        """Add a learned correction pattern"""
        # Check if similar correction exists
        existing = await self.select_one(
            "learned_corrections",
            "*",
            "trigger_pattern = ? AND tool_name IS ? AND action_name IS ?",
            (trigger_pattern, tool_name, action_name)
        )
        
        if existing:
            # Increase confidence
            await self.update(
                "learned_corrections",
                {
                    "confidence": min(existing['confidence'] + 0.1, 1.0),
                    "correct_behavior": correct_behavior,
                    "wrong_behavior": wrong_behavior or existing['wrong_behavior']
                },
                "id = ?",
                (existing['id'],)
            )
            return existing['id']
        else:
            return await self.insert("learned_corrections", {
                "trigger_pattern": trigger_pattern,
                "wrong_behavior": wrong_behavior,
                "correct_behavior": correct_behavior,
                "tool_name": tool_name,
                "action_name": action_name,
                "confidence": 1.0,
                "use_count": 0,
                "session_id": session_id,
                "is_permanent": 1 if is_permanent else 0,
                "created_at": datetime.now().isoformat()
            })
    
    async def get_relevant_corrections(self, user_input: str, tool_name: str = None) -> List[Dict[str, Any]]:
        """Get corrections relevant to current context"""
        corrections = []
        
        # First, apply confidence decay to old corrections
        await self._decay_old_corrections()
        
        # Get tool-specific corrections (permanent only or matching session)
        if tool_name:
            tool_corrections = await self.select(
                "learned_corrections",
                "*",
                "tool_name = ? AND confidence >= 0.3 AND is_permanent = 1",
                (tool_name,),
                order_by="confidence DESC",
                limit=10
            )
            corrections.extend(tool_corrections)
        
        # Get pattern-matching corrections (permanent only)
        all_corrections = await self.select(
            "learned_corrections",
            "*",
            "confidence >= 0.3 AND is_permanent = 1",
            order_by="confidence DESC",
            limit=50
        )
        
        # Filter by trigger pattern match
        user_lower = user_input.lower()
        for corr in all_corrections:
            trigger = corr.get('trigger_pattern', '').lower()
            if trigger and trigger in user_lower:
                if corr not in corrections:
                    corrections.append(corr)
        
        return corrections[:10]  # Return top 10
    
    async def get_session_corrections(self, session_id: str) -> List[Dict[str, Any]]:
        """Get corrections specific to current session"""
        return await self.select(
            "learned_corrections",
            "*",
            "session_id = ? AND is_permanent = 0",
            (session_id,),
            order_by="created_at DESC"
        )
    
    async def cleanup_session_corrections(self, session_id: str):
        """Remove session-specific corrections when session ends"""
        await self.delete(
            "learned_corrections",
            "session_id = ? AND is_permanent = 0",
            (session_id,)
        )
    
    async def _decay_old_corrections(self):
        """Apply confidence decay to corrections not used recently"""
        try:
            # Decay corrections not used in 7 days
            seven_days_ago = (datetime.now() - __import__('datetime').timedelta(days=7)).isoformat()
            
            # Get old corrections with high confidence
            old_corrections = await self.execute_raw(
                """SELECT id, confidence FROM learned_corrections 
                   WHERE (last_used IS NULL OR last_used < ?) AND confidence > 0.3""",
                (seven_days_ago,)
            )
            
            for corr in old_corrections:
                # Decay by 10%
                new_confidence = max(corr['confidence'] * 0.9, 0.1)
                await self.update(
                    "learned_corrections",
                    {"confidence": new_confidence},
                    "id = ?",
                    (corr['id'],)
                )
        except Exception as e:
            logging.debug(f"Correction decay error: {e}")
    
    async def mark_correction_used(self, correction_id: int):
        """Mark a correction as used (increases confidence)"""
        existing = await self.select_one("learned_corrections", "*", "id = ?", (correction_id,))
        if existing:
            await self.update(
                "learned_corrections",
                {
                    "use_count": existing['use_count'] + 1,
                    "last_used": datetime.now().isoformat()
                },
                "id = ?",
                (correction_id,)
            )
    
    async def log_conversation_exchange(
        self,
        session_id: str,
        user_input: str,
        ai_response: str,
        tools_used: List[str] = None,
        tool_results: List[Dict] = None,
        mood: str = None,
        topics: List[str] = None
    ) -> int:
        """Log a conversation exchange (infinite history)"""
        return await self.insert("conversation_exchanges", {
            "session_id": session_id,
            "user_input": user_input,
            "ai_response": ai_response,
            "tools_used": json.dumps(tools_used) if tools_used else None,
            "tool_results": json.dumps(tool_results) if tool_results else None,
            "mood": mood,
            "topics": json.dumps(topics) if topics else None,
            "created_at": datetime.now().isoformat()
        })
    
    async def get_conversation_history(
        self, 
        session_id: str = None, 
        limit: int = 50,
        search_query: str = None
    ) -> List[Dict[str, Any]]:
        """Get conversation history, optionally filtered"""
        if search_query:
            return await self.execute_raw(
                """SELECT * FROM conversation_exchanges 
                   WHERE user_input LIKE ? OR ai_response LIKE ?
                   ORDER BY created_at DESC LIMIT ?""",
                (f"%{search_query}%", f"%{search_query}%", limit)
            )
        elif session_id:
            return await self.select(
                "conversation_exchanges",
                "*",
                "session_id = ?",
                (session_id,),
                order_by="created_at DESC",
                limit=limit
            )
        else:
            return await self.select(
                "conversation_exchanges",
                "*",
                order_by="created_at DESC",
                limit=limit
            )
    
    async def update_tool_pattern(
        self,
        tool_name: str,
        action_name: str,
        success: bool,
        duration_ms: int = None,
        params: Dict[str, Any] = None
    ):
        """Update tool usage patterns for optimization"""
        existing = await self.select_one(
            "tool_patterns",
            "*",
            "tool_name = ? AND action_name = ?",
            (tool_name, action_name)
        )
        
        if existing:
            # Update stats
            total = existing['total_uses'] + 1
            success_count = int(existing['success_rate'] * existing['total_uses'])
            if success:
                success_count += 1
            new_rate = success_count / total
            
            avg_duration = existing['avg_duration_ms']
            if duration_ms and avg_duration:
                avg_duration = int((avg_duration * existing['total_uses'] + duration_ms) / total)
            elif duration_ms:
                avg_duration = duration_ms
            
            await self.update(
                "tool_patterns",
                {
                    "success_rate": new_rate,
                    "avg_duration_ms": avg_duration,
                    "total_uses": total,
                    "last_used": datetime.now().isoformat()
                },
                "id = ?",
                (existing['id'],)
            )
        else:
            await self.insert("tool_patterns", {
                "tool_name": tool_name,
                "action_name": action_name,
                "success_rate": 1.0 if success else 0.0,
                "avg_duration_ms": duration_ms,
                "total_uses": 1,
                "last_used": datetime.now().isoformat()
            })
    
    async def get_tool_insights(self, tool_name: str, action_name: str = None) -> Dict[str, Any]:
        """Get insights about tool usage patterns"""
        insights = {
            "success_rate": None,
            "avg_duration_ms": None,
            "total_uses": 0,
            "is_reliable": True,
            "warning": None
        }
        
        if action_name:
            pattern = await self.select_one(
                "tool_patterns", "*",
                "tool_name = ? AND action_name = ?",
                (tool_name, action_name)
            )
            if pattern:
                insights["success_rate"] = pattern["success_rate"]
                insights["avg_duration_ms"] = pattern["avg_duration_ms"]
                insights["total_uses"] = pattern["total_uses"]
                
                # Flag unreliable tools
                if pattern["total_uses"] >= 5 and pattern["success_rate"] < 0.5:
                    insights["is_reliable"] = False
                    insights["warning"] = f"This action has a {pattern['success_rate']*100:.0f}% success rate"
        else:
            # Get all patterns for this tool
            patterns = await self.select("tool_patterns", where="tool_name = ?", where_params=(tool_name,))
            if patterns:
                total_uses = sum(p["total_uses"] for p in patterns)
                weighted_rate = sum(p["success_rate"] * p["total_uses"] for p in patterns) / total_uses if total_uses > 0 else 1.0
                insights["success_rate"] = weighted_rate
                insights["total_uses"] = total_uses
                
                if total_uses >= 10 and weighted_rate < 0.5:
                    insights["is_reliable"] = False
                    insights["warning"] = f"This tool has a {weighted_rate*100:.0f}% overall success rate"
        
        # Get recent errors for this tool
        recent_errors = await self.select(
            "error_patterns",
            where="tool_name = ?",
            where_params=(tool_name,),
            order_by="last_occurred DESC",
            limit=3
        )
        if recent_errors:
            insights["recent_errors"] = [
                {"type": e["error_type"], "count": e["occurrence_count"], "solution": e["solution"]}
                for e in recent_errors
            ]
        
        return insights
    
    async def log_error_pattern(
        self,
        tool_name: str,
        action_name: str,
        error_type: str,
        error_message: str,
        context: Dict[str, Any] = None,
        solution: str = None
    ):
        """Log an error pattern to avoid repeating"""
        # Check if similar error exists
        existing = await self.select_one(
            "error_patterns",
            "*",
            "tool_name = ? AND action_name = ? AND error_type = ?",
            (tool_name, action_name, error_type)
        )
        
        if existing:
            await self.update(
                "error_patterns",
                {
                    "occurrence_count": existing['occurrence_count'] + 1,
                    "last_occurred": datetime.now().isoformat(),
                    "solution": solution or existing['solution']
                },
                "id = ?",
                (existing['id'],)
            )
        else:
            await self.insert("error_patterns", {
                "tool_name": tool_name,
                "action_name": action_name,
                "error_type": error_type,
                "error_message": error_message,
                "context": json.dumps(context) if context else None,
                "solution": solution,
                "occurrence_count": 1,
                "last_occurred": datetime.now().isoformat()
            })
    
    async def get_error_solutions(self, tool_name: str, action_name: str, error_type: str = None) -> List[Dict[str, Any]]:
        """Get known solutions for errors"""
        if error_type:
            return await self.select(
                "error_patterns",
                "*",
                "tool_name = ? AND action_name = ? AND error_type = ? AND solution IS NOT NULL",
                (tool_name, action_name, error_type),
                order_by="occurrence_count DESC"
            )
        else:
            return await self.select(
                "error_patterns",
                "*",
                "tool_name = ? AND action_name = ? AND solution IS NOT NULL",
                (tool_name, action_name),
                order_by="occurrence_count DESC"
            )
    
    async def get_history_stats(self) -> Dict[str, Any]:
        """Get statistics about stored history"""
        return {
            "total_exchanges": await self.count("conversation_exchanges"),
            "total_actions": await self.count("actions"),
            "total_feedback": await self.count("user_feedback"),
            "total_corrections": await self.count("learned_corrections"),
            "total_error_patterns": await self.count("error_patterns"),
            "total_tool_patterns": await self.count("tool_patterns")
        }
    
    # ==================== Export/Import ====================
    
    async def export_to_json(self, output_file: Union[str, Path] = "sakura_memory_export.json") -> bool:
        """Export all data to JSON for transparency"""
        if not self._initialized:
            return False
        
        output_path = Path(output_file) if isinstance(output_file, str) else output_file
        
        try:
            export_data = {}
            
            tables = [
                "subjects", "events", "tasks", "actions", "user_info",
                "facts", "discovered_locations", "scripts", "conversations",
                "topics", "important_dates", "session_stats"
            ]
            
            for table in tables:
                export_data[table] = await self.select(table)
            
            import aiofiles
            async with aiofiles.open(str(output_path), 'w') as f:
                await f.write(json.dumps(export_data, indent=2, default=str))
            
            logging.info(f"Exported database to {output_path}")
            return True
        except Exception as e:
            logging.error(f"Export error: {e}")
            return False
    
    async def import_from_legacy_json(self, memory_file: Union[str, Path] = "sakura_memory.json") -> bool:
        """Import data from legacy JSON memory file"""
        if not self._initialized:
            return False
        
        memory_path = Path(memory_file) if isinstance(memory_file, str) else memory_file
        
        try:
            import aiofiles
            async with aiofiles.open(str(memory_path), 'r') as f:
                content = await f.read()
                legacy_data = json.loads(content)
            
            # Import user_info
            for key, value in legacy_data.get("user_info", {}).items():
                await self.insert("user_info", {"key": key, "value": str(value)})
            
            # Import facts
            for fact in legacy_data.get("facts", []):
                await self.insert("facts", {
                    "content": fact.get("content", str(fact)),
                    "category": fact.get("category", "general"),
                    "created_at": fact.get("timestamp", datetime.now().isoformat())
                })
            
            # Import discovered_locations
            for loc in legacy_data.get("discovered_locations", []):
                name = loc.get("key", "").replace("app_path_", "").replace("app_", "")
                path_value = loc.get("value", "")
                # Extract actual path from value string
                if " at " in path_value:
                    path = path_value.split(" at ")[-1]
                elif ": " in path_value:
                    path = path_value.split(": ")[-1]
                else:
                    path = path_value
                
                if name and path:
                    await self.upsert_location("app_path", name, path)
            
            # Import scripts
            for script in legacy_data.get("scripts_created", []):
                await self.insert("scripts", {
                    "name": script.get("name", ""),
                    "path": script.get("path", ""),
                    "script_type": script.get("type", ""),
                    "description": script.get("description", ""),
                    "created_at": script.get("timestamp", datetime.now().isoformat())
                })
            
            # Import topics
            for topic_key, topic_data in legacy_data.get("topics_discussed", {}).items():
                await self.insert("topics", {
                    "name": topic_key,
                    "mention_count": topic_data.get("count", 1),
                    "first_mentioned": topic_data.get("first_discussed", datetime.now().isoformat()),
                    "last_mentioned": topic_data.get("last_discussed", datetime.now().isoformat())
                })
            
            # Import important_dates
            for name, date_val in legacy_data.get("important_dates", {}).items():
                await self.insert("important_dates", {
                    "name": name,
                    "date_value": str(date_val)
                })
            
            # Import action_log as actions
            for action in legacy_data.get("action_log", []):
                value = action.get("value", "")
                # Parse action string like "[2025-12-25 10:58:18] system_info.get_user_folders -> success"
                parts = value.split("] ", 1)
                if len(parts) == 2:
                    action_part = parts[1]
                    if " -> " in action_part:
                        tool_action, status = action_part.rsplit(" -> ", 1)
                        if "." in tool_action:
                            tool_name, action_name = tool_action.split(".", 1)
                            # Extract action name without parameters
                            if " (" in action_name:
                                action_name = action_name.split(" (")[0]
                            
                            await self.insert("actions", {
                                "tool_name": tool_name.strip(),
                                "action_name": action_name.strip(),
                                "status": status.strip(),
                                "created_at": action.get("timestamp", datetime.now().isoformat())
                            })
            
            logging.info(f"Imported legacy data from {memory_path}")
            return True
        except FileNotFoundError:
            logging.info(f"No legacy file found: {memory_path}")
            return True
        except Exception as e:
            logging.error(f"Import error: {e}")
            return False
    
    # ==================== Cleanup ====================
    
    async def cleanup(self):
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._initialized = False
            logging.info("Database connection closed")
    
    async def prune_old_data(
        self,
        exchange_days: int = 90,
        action_days: int = 30,
        error_days: int = 60,
        keep_high_value: bool = True
    ) -> Dict[str, int]:
        """Prune old data to keep database size manageable"""
        if not self._initialized:
            return {}
        
        pruned = {
            "exchanges": 0,
            "actions": 0,
            "errors": 0,
            "corrections": 0,
            "fts": 0
        }
        
        try:
            from datetime import timedelta
            now = datetime.now()
            
            # Prune old conversation exchanges (keep last N days)
            exchange_cutoff = (now - timedelta(days=exchange_days)).isoformat()
            if keep_high_value:
                # Keep exchanges with feedback
                result = await self.execute_raw(
                    """DELETE FROM conversation_exchanges 
                       WHERE created_at < ? AND user_feedback_id IS NULL""",
                    (exchange_cutoff,)
                )
            else:
                result = await self.execute_raw(
                    "DELETE FROM conversation_exchanges WHERE created_at < ?",
                    (exchange_cutoff,)
                )
            pruned["exchanges"] = len(result) if result else 0
            
            # Prune old actions (keep last N days)
            action_cutoff = (now - timedelta(days=action_days)).isoformat()
            await self.execute_raw(
                "DELETE FROM actions WHERE created_at < ?",
                (action_cutoff,)
            )
            
            # Prune old error patterns with no solution
            error_cutoff = (now - timedelta(days=error_days)).isoformat()
            await self.execute_raw(
                "DELETE FROM error_patterns WHERE last_occurred < ? AND solution IS NULL",
                (error_cutoff,)
            )
            
            # Prune low-confidence corrections that haven't been used
            await self.execute_raw(
                """DELETE FROM learned_corrections 
                   WHERE confidence < 0.2 AND use_count = 0 
                   AND created_at < ?""",
                ((now - timedelta(days=30)).isoformat(),)
            )
            
            # Clean up orphaned FTS entries
            await self.execute_raw(
                """DELETE FROM memory_fts WHERE source_id NOT IN (
                    SELECT CAST(id AS TEXT) FROM facts WHERE source = 'fact'
                    UNION SELECT CAST(id AS TEXT) FROM user_info WHERE source = 'user_info'
                    UNION SELECT CAST(id AS TEXT) FROM conversations WHERE source = 'conversation'
                )"""
            )
            
            # Vacuum to reclaim space
            await self._connection.execute("VACUUM")
            await self._connection.commit()
            
            logging.info(f"Database pruned: {pruned}")
            return pruned
        except Exception as e:
            logging.error(f"Prune error: {e}")
            return pruned
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database size and table statistics"""
        if not self._initialized:
            return {}
        
        stats = {}
        tables = [
            "subjects", "events", "tasks", "actions", "user_info", "facts",
            "discovered_locations", "scripts", "conversations", "topics",
            "important_dates", "session_stats", "user_feedback", "learned_corrections",
            "conversation_exchanges", "tool_patterns", "error_patterns"
        ]
        
        for table in tables:
            try:
                count = await self.count(table)
                stats[table] = count
            except Exception:
                stats[table] = 0
        
        # Get database file size
        try:
            import os
            if self.db_path.exists():
                stats["file_size_mb"] = os.path.getsize(self.db_path) / (1024 * 1024)
        except Exception:
            pass
        
        return stats


# Singleton instance
_db_instance: Optional[DatabaseManager] = None


async def get_database(db_path: Union[str, Path] = "sakura.db") -> DatabaseManager:
    """Get or create database instance"""
    global _db_instance
    
    if _db_instance is None:
        _db_instance = DatabaseManager(db_path)
        await _db_instance.initialize()
    
    return _db_instance
