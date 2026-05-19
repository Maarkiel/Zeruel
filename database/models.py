from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.connection import Database


# --------------- Categories ---------------

async def create_category(db: Database, name: str, description: str | None = None) -> int:
    assert db.db is not None
    cursor = await db.db.execute(
        "INSERT INTO categories (name, description) VALUES (?, ?)",
        (name, description),
    )
    await db.db.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


async def get_categories(db: Database) -> list[dict[str, object]]:
    assert db.db is not None
    cursor = await db.db.execute("SELECT * FROM categories ORDER BY name")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_category(db: Database, category_id: int) -> dict[str, object] | None:
    assert db.db is not None
    cursor = await db.db.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_category_by_name(db: Database, name: str) -> dict[str, object] | None:
    assert db.db is not None
    cursor = await db.db.execute("SELECT * FROM categories WHERE name = ?", (name,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def update_category(db: Database, category_id: int, name: str) -> None:
    assert db.db is not None
    await db.db.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
    await db.db.commit()


async def delete_category(db: Database, category_id: int) -> bool:
    assert db.db is not None
    cursor = await db.db.execute(
        "SELECT COUNT(*) as cnt FROM questions WHERE category_id = ?", (category_id,)
    )
    row = await cursor.fetchone()
    if row and dict(row)["cnt"] > 0:
        return False
    await db.db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    await db.db.commit()
    return True


# --------------- Questions ---------------

async def create_question(
    db: Database,
    category_id: int,
    q_type: str,
    content: str,
    options: list[str] | None = None,
    correct_answer: str | None = None,
    model_answer: str | None = None,
    explanation: str | None = None,
    max_points: int = 1,
    difficulty: int = 1,
    created_by: str | None = None,
) -> int:
    assert db.db is not None
    options_json = json.dumps(options, ensure_ascii=False) if options else None
    cursor = await db.db.execute(
        """INSERT INTO questions
        (category_id, type, content, options, correct_answer, model_answer,
         explanation, max_points, difficulty, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            category_id, q_type, content, options_json, correct_answer,
            model_answer, explanation, max_points, difficulty, created_by,
        ),
    )
    await db.db.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


async def get_question(db: Database, question_id: int) -> dict[str, object] | None:
    assert db.db is not None
    cursor = await db.db.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    data = dict(row)
    if data.get("options"):
        data["options"] = json.loads(str(data["options"]))
    return data


async def get_questions(
    db: Database,
    category_id: int | None = None,
    q_type: str | None = None,
    difficulty: int | None = None,
    active_only: bool = True,
) -> list[dict[str, object]]:
    assert db.db is not None
    query = "SELECT * FROM questions WHERE 1=1"
    params: list[object] = []
    if active_only:
        query += " AND active = 1"
    if category_id is not None:
        query += " AND category_id = ?"
        params.append(category_id)
    if q_type is not None:
        query += " AND type = ?"
        params.append(q_type)
    if difficulty is not None:
        query += " AND difficulty = ?"
        params.append(difficulty)
    query += " ORDER BY id"
    cursor = await db.db.execute(query, params)
    rows = await cursor.fetchall()
    results = []
    for r in rows:
        data = dict(r)
        if data.get("options"):
            data["options"] = json.loads(str(data["options"]))
        results.append(data)
    return results


async def update_question(db: Database, question_id: int, **kwargs: object) -> None:
    assert db.db is not None
    if "options" in kwargs and isinstance(kwargs["options"], list):
        kwargs["options"] = json.dumps(kwargs["options"], ensure_ascii=False)
    kwargs["updated_at"] = datetime.now().isoformat()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [question_id]
    await db.db.execute(f"UPDATE questions SET {sets} WHERE id = ?", values)
    await db.db.commit()


async def delete_question(db: Database, question_id: int) -> None:
    assert db.db is not None
    await db.db.execute("UPDATE questions SET active = 0 WHERE id = ?", (question_id,))
    await db.db.commit()


async def count_questions(
    db: Database,
    category_id: int | None = None,
    q_type: str | None = None,
) -> int:
    assert db.db is not None
    query = "SELECT COUNT(*) as cnt FROM questions WHERE active = 1"
    params: list[object] = []
    if category_id is not None:
        query += " AND category_id = ?"
        params.append(category_id)
    if q_type is not None:
        query += " AND type = ?"
        params.append(q_type)
    cursor = await db.db.execute(query, params)
    row = await cursor.fetchone()
    return int(dict(row)["cnt"]) if row else 0


async def get_random_questions(
    db: Database,
    q_type: str,
    count: int,
    category_id: int | None = None,
    difficulty: int | None = None,
    exclude_ids: list[int] | None = None,
) -> list[dict[str, object]]:
    assert db.db is not None
    query = "SELECT * FROM questions WHERE active = 1 AND type = ?"
    params: list[object] = [q_type]
    if category_id is not None:
        query += " AND category_id = ?"
        params.append(category_id)
    if difficulty is not None:
        query += " AND difficulty = ?"
        params.append(difficulty)
    if exclude_ids:
        placeholders = ",".join("?" * len(exclude_ids))
        query += f" AND id NOT IN ({placeholders})"
        params.extend(exclude_ids)
    query += " ORDER BY RANDOM() LIMIT ?"
    params.append(count)
    cursor = await db.db.execute(query, params)
    rows = await cursor.fetchall()
    results = []
    for r in rows:
        data = dict(r)
        if data.get("options"):
            data["options"] = json.loads(str(data["options"]))
        results.append(data)
    return results


# --------------- Test Templates ---------------

async def create_test_template(
    db: Database,
    name: str,
    abcde_count: int = 7,
    descriptive_count: int = 3,
    time_limit_minutes: int = 15,
    passing_threshold: int = 60,
    category_id: int | None = None,
    difficulty: int | None = None,
    description: str | None = None,
    created_by: str | None = None,
) -> int:
    assert db.db is not None
    cursor = await db.db.execute(
        """INSERT INTO test_templates
        (name, description, category_id, abcde_count, descriptive_count,
         time_limit_minutes, passing_threshold, difficulty, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            name, description, category_id, abcde_count, descriptive_count,
            time_limit_minutes, passing_threshold, difficulty, created_by,
        ),
    )
    await db.db.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


async def get_test_templates(db: Database) -> list[dict[str, object]]:
    assert db.db is not None
    cursor = await db.db.execute("SELECT * FROM test_templates ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_test_template(db: Database, template_id: int) -> dict[str, object] | None:
    assert db.db is not None
    cursor = await db.db.execute("SELECT * FROM test_templates WHERE id = ?", (template_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


# --------------- Test Instances ---------------

async def create_test_instance(
    db: Database,
    user_id: str,
    guild_id: str,
    time_limit_minutes: int,
    passing_threshold: int,
    template_id: int | None = None,
    abcde_total: int = 0,
    descriptive_total: int = 0,
) -> int:
    assert db.db is not None
    cursor = await db.db.execute(
        """INSERT INTO test_instances
        (template_id, user_id, guild_id, time_limit_minutes, passing_threshold,
         abcde_total, descriptive_total)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (template_id, user_id, guild_id, time_limit_minutes, passing_threshold,
         abcde_total, descriptive_total),
    )
    await db.db.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


async def get_test_instance(db: Database, instance_id: int) -> dict[str, object] | None:
    assert db.db is not None
    cursor = await db.db.execute("SELECT * FROM test_instances WHERE id = ?", (instance_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_user_tests(db: Database, user_id: str) -> list[dict[str, object]]:
    assert db.db is not None
    cursor = await db.db.execute(
        "SELECT * FROM test_instances WHERE user_id = ? ORDER BY started_at DESC",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def update_test_instance(db: Database, instance_id: int, **kwargs: object) -> None:
    assert db.db is not None
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [instance_id]
    await db.db.execute(f"UPDATE test_instances SET {sets} WHERE id = ?", values)
    await db.db.commit()


async def get_pending_grading_tests(db: Database, guild_id: str | None = None) -> list[dict[str, object]]:
    assert db.db is not None
    query = "SELECT * FROM test_instances WHERE status = 'grading'"
    params: list[object] = []
    if guild_id:
        query += " AND guild_id = ?"
        params.append(guild_id)
    query += " ORDER BY completed_at ASC"
    cursor = await db.db.execute(query, params)
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


# --------------- Test Answers ---------------

async def create_test_answer(
    db: Database,
    test_instance_id: int,
    question_id: int,
    answer: str | None = None,
    is_correct: int | None = None,
    points_awarded: int | None = None,
) -> int:
    assert db.db is not None
    cursor = await db.db.execute(
        """INSERT INTO test_answers
        (test_instance_id, question_id, answer, is_correct, points_awarded)
        VALUES (?, ?, ?, ?, ?)""",
        (test_instance_id, question_id, answer, is_correct, points_awarded),
    )
    await db.db.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


async def get_test_answers(db: Database, test_instance_id: int) -> list[dict[str, object]]:
    assert db.db is not None
    cursor = await db.db.execute(
        """SELECT ta.*, q.content as question_content, q.type as question_type,
           q.correct_answer, q.model_answer, q.explanation, q.options, q.max_points
        FROM test_answers ta
        JOIN questions q ON ta.question_id = q.id
        WHERE ta.test_instance_id = ?
        ORDER BY ta.id""",
        (test_instance_id,),
    )
    rows = await cursor.fetchall()
    results = []
    for r in rows:
        data = dict(r)
        if data.get("options"):
            data["options"] = json.loads(str(data["options"]))
        results.append(data)
    return results


async def get_ungraded_answers(db: Database, guild_id: str | None = None) -> list[dict[str, object]]:
    assert db.db is not None
    query = """
        SELECT ta.*, q.content as question_content, q.model_answer, q.max_points,
               ti.user_id, ti.guild_id, ti.id as test_id
        FROM test_answers ta
        JOIN questions q ON ta.question_id = q.id
        JOIN test_instances ti ON ta.test_instance_id = ti.id
        WHERE ta.is_correct IS NULL
    """
    params: list[object] = []
    if guild_id:
        query += " AND ti.guild_id = ?"
        params.append(guild_id)
    query += " ORDER BY ta.answered_at ASC"
    cursor = await db.db.execute(query, params)
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def grade_answer(
    db: Database,
    answer_id: int,
    points_awarded: int,
    graded_by: str,
    comment: str | None = None,
) -> None:
    assert db.db is not None
    is_correct = 1 if points_awarded > 0 else 0
    await db.db.execute(
        """UPDATE test_answers
        SET points_awarded = ?, is_correct = ?, admin_comment = ?,
            graded_at = CURRENT_TIMESTAMP, graded_by = ?
        WHERE id = ?""",
        (points_awarded, is_correct, comment, graded_by, answer_id),
    )
    await db.db.commit()


async def check_test_fully_graded(db: Database, test_instance_id: int) -> bool:
    assert db.db is not None
    cursor = await db.db.execute(
        "SELECT COUNT(*) as cnt FROM test_answers WHERE test_instance_id = ? AND is_correct IS NULL",
        (test_instance_id,),
    )
    row = await cursor.fetchone()
    return row is not None and int(dict(row)["cnt"]) == 0


async def calculate_test_score(db: Database, test_instance_id: int) -> dict[str, object]:
    assert db.db is not None
    instance = await get_test_instance(db, test_instance_id)
    assert instance is not None

    cursor = await db.db.execute(
        """SELECT ta.*, q.type, q.max_points
        FROM test_answers ta
        JOIN questions q ON ta.question_id = q.id
        WHERE ta.test_instance_id = ?""",
        (test_instance_id,),
    )
    rows = await cursor.fetchall()

    abcde_score = 0
    abcde_total = 0
    descriptive_score = 0
    descriptive_total = 0

    for r in rows:
        answer = dict(r)
        if answer["type"] == "abcde":
            abcde_total += int(answer["max_points"])
            if answer["points_awarded"]:
                abcde_score += int(answer["points_awarded"])
        else:
            descriptive_total += int(answer["max_points"])
            if answer["points_awarded"]:
                descriptive_score += int(answer["points_awarded"])

    total_score = abcde_score + descriptive_score
    total_max = abcde_total + descriptive_total
    total_percent = (total_score / total_max * 100) if total_max > 0 else 0
    threshold = int(instance["passing_threshold"]) if instance["passing_threshold"] else 60
    passed = 1 if total_percent >= threshold else 0

    await update_test_instance(
        db, test_instance_id,
        abcde_score=abcde_score,
        abcde_total=abcde_total,
        descriptive_score=descriptive_score,
        descriptive_total=descriptive_total,
        total_percent=round(total_percent, 1),
        passed=passed,
    )

    return {
        "abcde_score": abcde_score,
        "abcde_total": abcde_total,
        "descriptive_score": descriptive_score,
        "descriptive_total": descriptive_total,
        "total_percent": round(total_percent, 1),
        "passed": passed,
    }


# --------------- Study ---------------

async def create_study_session(
    db: Database, user_id: str, category_id: int | None = None
) -> int:
    assert db.db is not None
    cursor = await db.db.execute(
        "INSERT INTO study_sessions (user_id, category_id) VALUES (?, ?)",
        (user_id, category_id),
    )
    await db.db.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


async def update_study_session(db: Database, session_id: int, **kwargs: object) -> None:
    assert db.db is not None
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [session_id]
    await db.db.execute(f"UPDATE study_sessions SET {sets} WHERE id = ?", values)
    await db.db.commit()


async def update_study_progress(
    db: Database, user_id: str, question_id: int, correct: bool
) -> None:
    assert db.db is not None
    existing = await db.db.execute(
        "SELECT * FROM study_progress WHERE user_id = ? AND question_id = ?",
        (user_id, question_id),
    )
    row = await existing.fetchone()

    if row:
        data = dict(row)
        times_seen = int(data["times_seen"]) + 1
        times_correct = int(data["times_correct"]) + (1 if correct else 0)
        needs_review = 0 if correct else 1
        await db.db.execute(
            """UPDATE study_progress
            SET times_seen = ?, times_correct = ?, needs_review = ?,
                last_seen = CURRENT_TIMESTAMP
            WHERE user_id = ? AND question_id = ?""",
            (times_seen, times_correct, needs_review, user_id, question_id),
        )
    else:
        await db.db.execute(
            """INSERT INTO study_progress
            (user_id, question_id, times_seen, times_correct, needs_review, last_seen)
            VALUES (?, ?, 1, ?, ?, CURRENT_TIMESTAMP)""",
            (user_id, question_id, 1 if correct else 0, 0 if correct else 1),
        )
    await db.db.commit()


async def get_review_questions(
    db: Database, user_id: str, category_id: int | None = None
) -> list[dict[str, object]]:
    assert db.db is not None
    query = """
        SELECT q.* FROM study_progress sp
        JOIN questions q ON sp.question_id = q.id
        WHERE sp.user_id = ? AND sp.needs_review = 1 AND q.active = 1 AND q.type = 'abcde'
    """
    params: list[object] = [user_id]
    if category_id is not None:
        query += " AND q.category_id = ?"
        params.append(category_id)
    query += " ORDER BY sp.last_seen ASC"
    cursor = await db.db.execute(query, params)
    rows = await cursor.fetchall()
    results = []
    for r in rows:
        data = dict(r)
        if data.get("options"):
            data["options"] = json.loads(str(data["options"]))
        results.append(data)
    return results


# --------------- Stats ---------------

async def get_user_stats(db: Database, user_id: str) -> dict[str, object]:
    assert db.db is not None

    tests_cursor = await db.db.execute(
        """SELECT COUNT(*) as total,
           SUM(CASE WHEN status = 'graded' THEN 1 ELSE 0 END) as graded,
           SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passed,
           AVG(CASE WHEN total_percent IS NOT NULL THEN total_percent END) as avg_percent,
           MAX(total_percent) as best,
           MIN(CASE WHEN total_percent IS NOT NULL THEN total_percent END) as worst
        FROM test_instances WHERE user_id = ?""",
        (user_id,),
    )
    tests_row = await tests_cursor.fetchone()
    tests = dict(tests_row) if tests_row else {}

    study_cursor = await db.db.execute(
        """SELECT COUNT(*) as sessions,
           SUM(questions_practiced) as total_practiced,
           SUM(correct_answers) as total_correct
        FROM study_sessions WHERE user_id = ?""",
        (user_id,),
    )
    study_row = await study_cursor.fetchone()
    study = dict(study_row) if study_row else {}

    review_cursor = await db.db.execute(
        "SELECT COUNT(*) as cnt FROM study_progress WHERE user_id = ? AND needs_review = 1",
        (user_id,),
    )
    review_row = await review_cursor.fetchone()
    review_count = int(dict(review_row)["cnt"]) if review_row else 0

    pending_cursor = await db.db.execute(
        """SELECT COUNT(*) as cnt FROM test_answers ta
        JOIN test_instances ti ON ta.test_instance_id = ti.id
        WHERE ti.user_id = ? AND ta.is_correct IS NULL""",
        (user_id,),
    )
    pending_row = await pending_cursor.fetchone()
    pending_count = int(dict(pending_row)["cnt"]) if pending_row else 0

    return {
        "tests_total": tests.get("total", 0),
        "tests_graded": tests.get("graded", 0),
        "tests_passed": tests.get("passed", 0),
        "avg_percent": round(float(tests["avg_percent"]), 1) if tests.get("avg_percent") else None,
        "best_percent": tests.get("best"),
        "worst_percent": tests.get("worst"),
        "study_sessions": study.get("sessions", 0),
        "total_practiced": study.get("total_practiced", 0),
        "total_correct": study.get("total_correct", 0),
        "review_count": review_count,
        "pending_grading": pending_count,
    }


async def get_ranking(db: Database, guild_id: str | None = None) -> list[dict[str, object]]:
    assert db.db is not None
    query = """
        SELECT user_id,
           COUNT(*) as tests_count,
           AVG(CASE WHEN total_percent IS NOT NULL THEN total_percent END) as avg_score,
           (SELECT COUNT(*) FROM study_sessions ss WHERE ss.user_id = ti.user_id) as study_count
        FROM test_instances ti
        WHERE status = 'graded'
    """
    params: list[object] = []
    if guild_id:
        query += " AND guild_id = ?"
        params.append(guild_id)
    query += " GROUP BY user_id ORDER BY avg_score DESC"
    cursor = await db.db.execute(query, params)
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_question_stats(
    db: Database, category_id: int | None = None
) -> list[dict[str, object]]:
    assert db.db is not None
    query = """
        SELECT q.id, q.type, q.content, q.category_id,
           COUNT(ta.id) as times_used,
           SUM(CASE WHEN ta.is_correct = 1 THEN 1 ELSE 0 END) as times_correct,
           CASE WHEN COUNT(ta.id) > 0
                THEN ROUND(SUM(CASE WHEN ta.is_correct = 1 THEN 1.0 ELSE 0.0 END) / COUNT(ta.id) * 100, 1)
                ELSE NULL END as correctness_pct,
           AVG(ta.points_awarded) as avg_points
        FROM questions q
        LEFT JOIN test_answers ta ON q.id = ta.question_id
        WHERE q.active = 1
    """
    params: list[object] = []
    if category_id is not None:
        query += " AND q.category_id = ?"
        params.append(category_id)
    query += " GROUP BY q.id ORDER BY times_used DESC"
    cursor = await db.db.execute(query, params)
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


# --------------- Guild Config ---------------

async def get_guild_config(db: Database, guild_id: str) -> dict[str, object]:
    assert db.db is not None
    cursor = await db.db.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,))
    row = await cursor.fetchone()
    if row:
        return dict(row)
    await db.db.execute("INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)", (guild_id,))
    await db.db.commit()
    return {"guild_id": guild_id, "grading_channel_id": None, "test_results_channel_id": None,
            "admin_role_id": None, "moderator_role_id": None}


async def update_guild_config(db: Database, guild_id: str, **kwargs: object) -> None:
    assert db.db is not None
    await db.db.execute("INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)", (guild_id,))
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [guild_id]
    await db.db.execute(f"UPDATE guild_config SET {sets} WHERE guild_id = ?", values)
    await db.db.commit()
