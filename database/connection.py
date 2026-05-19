import aiosqlite
from config import DATABASE_PATH


class Database:
    def __init__(self) -> None:
        self.path = DATABASE_PATH
        self.db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.db = await aiosqlite.connect(self.path)
        self.db.row_factory = aiosqlite.Row
        await self.db.execute("PRAGMA journal_mode=WAL")
        await self.db.execute("PRAGMA foreign_keys=ON")
        await self._create_tables()

    async def close(self) -> None:
        if self.db:
            await self.db.close()

    async def _create_tables(self) -> None:
        assert self.db is not None
        await self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                options TEXT,
                correct_answer TEXT,
                model_answer TEXT,
                explanation TEXT,
                max_points INTEGER DEFAULT 1,
                difficulty INTEGER DEFAULT 1,
                active INTEGER DEFAULT 1,
                created_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );

            CREATE TABLE IF NOT EXISTS test_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                category_id INTEGER,
                abcde_count INTEGER DEFAULT 7,
                descriptive_count INTEGER DEFAULT 3,
                time_limit_minutes INTEGER DEFAULT 15,
                passing_threshold INTEGER DEFAULT 60,
                difficulty INTEGER,
                created_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );

            CREATE TABLE IF NOT EXISTS test_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER,
                user_id TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                status TEXT DEFAULT 'in_progress',
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                graded_at DATETIME,
                graded_by TEXT,
                abcde_score INTEGER DEFAULT 0,
                abcde_total INTEGER DEFAULT 0,
                descriptive_score INTEGER DEFAULT 0,
                descriptive_total INTEGER DEFAULT 0,
                total_percent REAL,
                passed INTEGER,
                time_limit_minutes INTEGER,
                passing_threshold INTEGER,
                FOREIGN KEY (template_id) REFERENCES test_templates(id)
            );

            CREATE TABLE IF NOT EXISTS test_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_instance_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                answer TEXT,
                is_correct INTEGER,
                points_awarded INTEGER,
                admin_comment TEXT,
                answered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                graded_at DATETIME,
                graded_by TEXT,
                FOREIGN KEY (test_instance_id) REFERENCES test_instances(id),
                FOREIGN KEY (question_id) REFERENCES questions(id)
            );

            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                category_id INTEGER,
                questions_practiced INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ended_at DATETIME,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );

            CREATE TABLE IF NOT EXISTS study_progress (
                user_id TEXT NOT NULL,
                question_id INTEGER NOT NULL,
                times_seen INTEGER DEFAULT 0,
                times_correct INTEGER DEFAULT 0,
                last_seen DATETIME,
                needs_review INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, question_id),
                FOREIGN KEY (question_id) REFERENCES questions(id)
            );

            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id TEXT PRIMARY KEY,
                grading_channel_id TEXT,
                test_results_channel_id TEXT,
                admin_role_id TEXT,
                moderator_role_id TEXT
            );
            """
        )
        await self.db.commit()
