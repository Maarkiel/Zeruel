from __future__ import annotations

import discord
from utils.helpers import difficulty_stars, progress_bar


def question_preview_embed(question: dict[str, object], stats: dict[str, object] | None = None) -> discord.Embed:
    q_type = "ABCDE" if question["type"] == "abcde" else "Opisowe"
    diff = difficulty_stars(int(question.get("difficulty", 1) or 1))
    embed = discord.Embed(
        title=f"\U0001f4cb Pytanie #{question['id']}",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="Info",
        value=f"Typ: **{q_type}** | Trudność: {diff}",
        inline=False,
    )
    embed.add_field(name="Treść", value=str(question["content"]), inline=False)

    if question["type"] == "abcde" and question.get("options"):
        options = question["options"]
        if isinstance(options, list):
            options_text = "\n".join(
                f"{'✅ ' if opt.startswith(str(question.get('correct_answer', ''))) else '   '}{opt}"
                for opt in options
            )
            embed.add_field(name="Opcje", value=options_text, inline=False)

    if question.get("explanation"):
        embed.add_field(name="\U0001f4a1 Wyjaśnienie", value=str(question["explanation"]), inline=False)

    if question["type"] == "descriptive" and question.get("model_answer"):
        embed.add_field(
            name="\U0001f4cc Wzorcowa odpowiedź",
            value=str(question["model_answer"]),
            inline=False,
        )
        embed.add_field(
            name="Maks. punktów",
            value=str(question.get("max_points", 10)),
            inline=True,
        )

    if stats:
        embed.add_field(
            name="\U0001f4ca Statystyki",
            value=f"Użyte: {stats.get('times_used', 0)} razy | Poprawność: {stats.get('correctness_pct', '—')}%",
            inline=False,
        )

    return embed


def test_start_embed(
    test_id: int,
    abcde_count: int,
    descriptive_count: int,
    time_limit: int,
    threshold: int,
    category_name: str | None = None,
) -> discord.Embed:
    total = abcde_count + descriptive_count
    cat = category_name or "Mix"
    embed = discord.Embed(
        title=f"\U0001f4dd Test #{test_id}",
        description=f"Kategoria: **{cat}**",
        color=discord.Color.gold(),
    )
    embed.add_field(name="Pytań", value=f"{total} ({abcde_count} ABCDE + {descriptive_count} opisowe)", inline=False)
    embed.add_field(name="Czas", value=f"{time_limit} minut", inline=True)
    embed.add_field(name="Próg zaliczenia", value=f"{threshold}%", inline=True)
    embed.set_footer(text="Test jest prywatny — odpowiedzi widoczne tylko dla Ciebie.")
    return embed


def test_question_embed(
    question: dict[str, object],
    current: int,
    total: int,
    time_remaining: str | None = None,
) -> discord.Embed:
    q_type = "ABCDE" if question["type"] == "abcde" else "Opisowe"
    bar = progress_bar(current - 1, total)
    embed = discord.Embed(
        title=f"\u2753 Pytanie {current}/{total} — {q_type}",
        description=str(question["content"]),
        color=discord.Color.blue() if question["type"] == "abcde" else discord.Color.purple(),
    )
    footer_parts = [f"Postęp: {bar} {current}/{total}"]
    if time_remaining:
        footer_parts.insert(0, f"\u23f1\ufe0f {time_remaining} pozostało")
    embed.set_footer(text=" | ".join(footer_parts))
    return embed


def test_result_embed(
    test_id: int,
    abcde_score: int,
    abcde_total: int,
    descriptive_score: int | None,
    descriptive_total: int,
    total_percent: float | None,
    passed: bool | None,
    has_ungraded: bool = False,
) -> discord.Embed:
    if has_ungraded:
        color = discord.Color.gold()
        status = "\u23f3 Oczekuje na ocenę"
    elif passed:
        color = discord.Color.green()
        status = "\u2705 ZALICZONY"
    else:
        color = discord.Color.red()
        status = "\u274c NIEZALICZONY"

    embed = discord.Embed(
        title=f"\U0001f4ca Wynik testu #{test_id}",
        color=color,
    )
    abcde_pct = round(abcde_score / abcde_total * 100, 1) if abcde_total > 0 else 0
    embed.add_field(
        name="ABCDE",
        value=f"{abcde_score}/{abcde_total} ({abcde_pct}%)",
        inline=True,
    )
    if has_ungraded:
        embed.add_field(
            name="Opisowe",
            value=f"{descriptive_total} odpowiedzi — oczekują na ocenę \u23f3",
            inline=True,
        )
    elif descriptive_total > 0:
        embed.add_field(
            name="Opisowe",
            value=f"{descriptive_score}/{descriptive_total}",
            inline=True,
        )
    if total_percent is not None:
        embed.add_field(name="Razem", value=f"{total_percent}%", inline=True)
    embed.add_field(name="Status", value=status, inline=False)
    return embed


def study_answer_embed(
    question: dict[str, object],
    user_answer: str,
    correct: bool,
    streak: int,
) -> discord.Embed:
    if correct:
        color = discord.Color.green()
        title = "\u2705 Poprawnie!"
    else:
        color = discord.Color.red()
        title = "\u274c Niepoprawnie"

    embed = discord.Embed(title=title, color=color)
    embed.add_field(name="Pytanie", value=str(question["content"]), inline=False)
    embed.add_field(name="Twoja odpowiedź", value=user_answer, inline=True)
    if question.get("correct_answer"):
        embed.add_field(name="Poprawna", value=str(question["correct_answer"]), inline=True)
    if question.get("explanation"):
        embed.add_field(name="\U0001f4a1 Wyjaśnienie", value=str(question["explanation"]), inline=False)
    if streak > 1:
        embed.set_footer(text=f"\U0001f525 Seria: {streak} z rzędu!")
    return embed


def user_stats_embed(
    user: discord.User | discord.Member,
    stats: dict[str, object],
) -> discord.Embed:
    embed = discord.Embed(
        title=f"\U0001f4ca Statystyki — {user.display_name}",
        color=discord.Color.blue(),
    )

    tests_total = stats.get("tests_total") or 0
    tests_passed = stats.get("tests_passed") or 0
    avg = stats.get("avg_percent")
    best = stats.get("best_percent")
    worst = stats.get("worst_percent")

    test_lines = [
        f"Ukończone: {tests_total}",
        f"Zaliczone: {tests_passed}",
    ]
    if avg is not None:
        test_lines.append(f"Średni wynik: {avg}%")
    if best is not None:
        test_lines.append(f"Najlepszy: {best}%")
    if worst is not None:
        test_lines.append(f"Najgorszy: {worst}%")
    embed.add_field(name="\U0001f4dd Testy", value="\n".join(test_lines), inline=False)

    study_sessions = stats.get("study_sessions") or 0
    total_practiced = stats.get("total_practiced") or 0
    review_count = stats.get("review_count") or 0
    study_lines = [
        f"Sesje: {study_sessions}",
        f"Pytań ćwiczonych: {total_practiced}",
        f"Do powtórki: {review_count}",
    ]
    embed.add_field(name="\U0001f9e0 Nauka", value="\n".join(study_lines), inline=False)

    pending = stats.get("pending_grading") or 0
    if pending > 0:
        embed.add_field(
            name="\u23f3 Oczekujące",
            value=f"Opisowe do oceny: {pending} odpowiedzi",
            inline=False,
        )

    return embed


def ranking_embed(ranking: list[dict[str, object]], guild: discord.Guild | None = None) -> discord.Embed:
    embed = discord.Embed(
        title="\U0001f3c6 Ranking moderatorów",
        color=discord.Color.gold(),
    )
    if not ranking:
        embed.description = "Brak danych — nikt jeszcze nie ukończył testu."
        return embed

    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]
    lines: list[str] = []
    for i, entry in enumerate(ranking[:15]):
        medal = medals[i] if i < 3 else f"{i + 1}."
        avg = round(float(entry["avg_score"]), 1) if entry.get("avg_score") else "—"
        lines.append(
            f"{medal} <@{entry['user_id']}> — "
            f"Testy: {entry['tests_count']} | Śr: {avg}% | "
            f"Nauka: {entry.get('study_count', 0)}"
        )
    embed.description = "\n".join(lines)
    return embed


def grading_embed(answer: dict[str, object]) -> discord.Embed:
    embed = discord.Embed(
        title=f"\U0001f4dd Ocena odpowiedzi #{answer['id']}",
        color=discord.Color.orange(),
    )
    embed.add_field(name="\U0001f464 Moderator", value=f"<@{answer['user_id']}>", inline=True)
    embed.add_field(name="\U0001f4cb Test", value=f"#{answer['test_id']}", inline=True)
    embed.add_field(name="\u2753 Pytanie", value=str(answer["question_content"]), inline=False)
    embed.add_field(name="\U0001f4dd Odpowiedź moderatora", value=str(answer.get("answer", "—")), inline=False)
    if answer.get("model_answer"):
        embed.add_field(name="\U0001f4cc Wzorcowa odpowiedź", value=str(answer["model_answer"]), inline=False)
    embed.add_field(name="Maks. punktów", value=str(answer.get("max_points", 10)), inline=True)
    return embed
