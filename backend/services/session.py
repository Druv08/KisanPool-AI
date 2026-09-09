from __future__ import annotations

import json
from typing import Any

from database import get_db_connection


class ConversationSession:
    """Persistent conversation state stored in SQLite."""

    def __init__(self, farmer_id: int) -> None:
        self.farmer_id = farmer_id

    def get(self) -> dict[str, Any] | None:
        connection = get_db_connection()

        try:
            row = connection.execute(
                """
                SELECT request_json
                FROM conversation_sessions
                WHERE farmer_id = ?
                """,
                (self.farmer_id,),
            ).fetchone()

            if row is None:
                print("SESSION GET: EMPTY")
                return None

            data = json.loads(row["request_json"])

            print("SESSION GET:", data)

            return data

        finally:
            connection.close()

    def update(self, request: dict[str, Any]) -> None:
        connection = get_db_connection()

        try:
            connection.execute(
                """
                INSERT INTO conversation_sessions
                    (farmer_id, request_json)
                VALUES (?, ?)
                ON CONFLICT(farmer_id)
                DO UPDATE SET
                    request_json = excluded.request_json
                """,
                (
                    self.farmer_id,
                    json.dumps(request),
                ),
            )

            connection.commit()

            print("SESSION SAVED:", request)

        finally:
            connection.close()

    def clear(self) -> None:
        connection = get_db_connection()

        try:
            connection.execute(
                """
                DELETE FROM conversation_sessions
                WHERE farmer_id = ?
                """,
                (self.farmer_id,),
            )

            connection.commit()

            print("SESSION CLEARED")

        finally:
            connection.close()