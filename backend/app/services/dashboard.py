from __future__ import annotations

from datetime import datetime

from ..db import db_session


def format_activity_time(value: str) -> str:
    try:
        created_at = datetime.fromisoformat(value)
    except ValueError:
        return value
    return created_at.strftime("%b %d, %Y %I:%M %p")


def get_dashboard_stats(user: dict) -> dict:
    with db_session() as connection:
        total_conversations = connection.execute(
            "SELECT COUNT(*) AS count FROM conversations WHERE user_id = ?",
            (user["id"],),
        ).fetchone()["count"]
        total_messages = connection.execute(
            "SELECT COUNT(*) AS count FROM messages WHERE user_id = ?",
            (user["id"],),
        ).fetchone()["count"]
        recent_activity = connection.execute(
            """
            SELECT title, description, activity_type, created_at
            FROM activities
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 8
            """,
            (user["id"],),
        ).fetchall()
        latest_conversation = connection.execute(
            """
            SELECT title, updated_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (user["id"],),
        ).fetchone()

    return {
        "user": {
            "id": user["id"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "email": user["email"],
            "phone": user.get("phone") or "",
            "created_at": user.get("created_at") or "",
            "member_since": format_activity_time(user["created_at"]) if user.get("created_at") else "Unknown",
        },
        "stats": {
            "total_conversations": total_conversations or 0,
            "total_messages": total_messages or 0,
            "recent_activity_count": len(recent_activity),
        },
        "latest_conversation": {
            "title": latest_conversation["title"] if latest_conversation else "No conversations yet",
            "display_time": format_activity_time(latest_conversation["updated_at"]) if latest_conversation else "",
        },
        "recent_activity": [
            {
                "title": item["title"],
                "description": item["description"],
                "type": item["activity_type"],
                "created_at": item["created_at"],
                "display_time": format_activity_time(item["created_at"]),
            }
            for item in recent_activity
        ],
    }


def get_user_history(user: dict, date: str | None = None) -> dict:
    query = """
            SELECT title, description, activity_type, created_at
            FROM activities
            WHERE user_id = ?
            """
    params = [user["id"]]
    if date:
        query += " AND created_at LIKE ?"
        params.append(f"{date}%")
    query += " ORDER BY created_at DESC LIMIT 50"

    with db_session() as connection:
        rows = connection.execute(query, params).fetchall()

    return {
        "items": [
            {
                "title": row["title"],
                "description": row["description"],
                "type": row["activity_type"],
                "created_at": row["created_at"],
                "display_time": format_activity_time(row["created_at"]),
            }
            for row in rows
        ]
    }
