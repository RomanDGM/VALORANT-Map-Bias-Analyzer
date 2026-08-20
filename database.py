# database.py — SQLite database management

import sqlite3
import os
from config import DB_PATH


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't already exist."""
    conn = get_connection()
    c = conn.cursor()

    # Matches table
    c.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id        TEXT PRIMARY KEY,
            map_name        TEXT NOT NULL,
            game_start      INTEGER,
            game_length     INTEGER,
            queue_id        TEXT
        )
    """)

    # Team results per match
    c.execute("""
        CREATE TABLE IF NOT EXISTS team_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id        TEXT NOT NULL,
            team_id         TEXT NOT NULL,   -- 'Red' or 'Blue'
            starting_side   TEXT NOT NULL,   -- 'attacker' or 'defender'
            rounds_won      INTEGER,
            rounds_lost     INTEGER,
            won             INTEGER,         -- 1 = win, 0 = loss
            FOREIGN KEY (match_id) REFERENCES matches(match_id)
        )
    """)

    # Aggregate map statistics
    c.execute("""
        CREATE TABLE IF NOT EXISTS map_stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            map_name        TEXT NOT NULL,
            attacker_wins   INTEGER DEFAULT 0,
            defender_wins   INTEGER DEFAULT 0,
            total_matches   INTEGER DEFAULT 0,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")


def insert_match(match_id, map_name, game_start, game_length, queue_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO matches (match_id, map_name, game_start, game_length, queue_id)
        VALUES (?, ?, ?, ?, ?)
    """, (match_id, map_name, game_start, game_length, queue_id))
    conn.commit()
    conn.close()


def insert_team_result(match_id, team_id, starting_side, rounds_won, rounds_lost, won):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO team_results (match_id, team_id, starting_side, rounds_won, rounds_lost, won)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (match_id, team_id, starting_side, rounds_won, rounds_lost, won))
    conn.commit()
    conn.close()


def get_all_matches():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM matches")
    rows = c.fetchall()
    conn.close()
    return rows


def get_team_results():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT m.map_name, tr.starting_side, tr.won
        FROM team_results tr
        JOIN matches m ON tr.match_id = m.match_id
    """)
    rows = c.fetchall()
    conn.close()
    return rows


def match_exists(match_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM matches WHERE match_id = ?", (match_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists
