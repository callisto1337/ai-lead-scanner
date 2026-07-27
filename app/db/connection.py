from collections.abc import Generator
from contextlib import contextmanager
from typing import cast

import psycopg
from psycopg import Connection
from psycopg.rows import DictRow, dict_row

from app.settings import DATABASE_URL


@contextmanager
def get_connection() -> Generator[Connection[DictRow], None, None]:
    connection = cast(
        Connection[DictRow],
        psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row,  # pyright: ignore[reportArgumentType]
        ),
    )

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()