import json
import time
import os
from sqlalchemy import create_engine, Column, String, Text, Float, MetaData, Table, Integer
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# --- Supabase Database Setup ---
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

if not SUPABASE_DB_URL:
    raise ValueError("SUPABASE_DB_URL is not set in the environment variables.")

engine = create_engine(SUPABASE_DB_URL)
metadata = MetaData()

# Define the cache table for API responses
cache_table = Table(
    'cache',
    metadata,
    Column('key', String, primary_key=True),
    Column('value', Text),
    Column('expiry', Float)
)

# Define the job queue table for asynchronous analysis tasks
job_queue_table = Table(
    'job_queue',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('chat_id', String, nullable=False),
    Column('match_details', Text, nullable=False), # Storing match details as a JSON string
    Column('status', String, default='pending') # e.g., pending, processing, done
)

# Create tables if they don't exist
metadata.create_all(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Caching Functions (Now using Supabase) ---

def cache_data(key, value, ttl):
    db_session = SessionLocal()
    try:
        expiry_time = time.time() + ttl
        serialized_value = json.dumps(value)

        # Upsert logic for PostgreSQL
        from sqlalchemy.dialects.postgresql import insert
        insert_stmt = insert(cache_table).values(key=key, value=serialized_value, expiry=expiry_time)
        on_conflict_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['key'],
            set_={'value': serialized_value, 'expiry': expiry_time}
        )
        db_session.execute(on_conflict_stmt)
        db_session.commit()
    finally:
        db_session.close()

def get_cached_data(key):
    db_session = SessionLocal()
    try:
        result = db_session.query(cache_table).filter(cache_table.c.key == key).first()
        if result and time.time() < result.expiry:
            return json.loads(result.value)
        return None
    finally:
        db_session.close()

# --- Job Queue Functions ---

def add_analysis_job(chat_id, match_details):
    """Adds a new analysis job to the Supabase job queue."""
    db_session = SessionLocal()
    try:
        job = {
            "chat_id": str(chat_id),
            "match_details": json.dumps(match_details),
            "status": "pending"
        }
        insert_stmt = job_queue_table.insert().values(**job)
        db_session.execute(insert_stmt)
        db_session.commit()
    finally:
        db_session.close()

def get_pending_jobs():
    """Retrieves all pending jobs from the queue."""
    db_session = SessionLocal()
    try:
        jobs = db_session.query(job_queue_table).filter(job_queue_table.c.status == 'pending').all()
        return jobs
    finally:
        db_session.close()

def update_job_status(job_id, status):
    """Updates the status of a specific job."""
    db_session = SessionLocal()
    try:
        db_session.query(job_queue_table).filter(job_queue_table.c.id == job_id).update({"status": status})
        db_session.commit()
    finally:
        db_session.close()

def delete_job(job_id):
    """Deletes a job from the queue (usually after completion)."""
    db_session = SessionLocal()
    try:
        db_session.query(job_queue_table).filter(job_queue_table.c.id == job_id).delete()
        db_session.commit()
    finally:
        db_session.close()

# --- Data Formatting Utilities (Unchanged) ---

def format_odds_for_ai(bookmakers_data):
    best_odds = {}
    for bookmaker in bookmakers_data:
        for market in bookmaker.get("markets", []):
            if market.get("key") == "h2h":
                for outcome in market.get("outcomes", []):
                    name = outcome["name"]
                    price = outcome["price"]
                    if name not in best_odds or price > best_odds[name]["price"]:
                        best_odds[name] = {"price": price, "bookmaker": bookmaker["title"]}
    return best_odds
