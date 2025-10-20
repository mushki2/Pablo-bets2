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

# Define the job queue table for asynchronous tasks
job_queue_table = Table(
    'job_queue',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('chat_id', String, nullable=False),
    Column('job_type', String, nullable=False, default='analysis'), # 'analysis' or 'arbitrage_scan'
    Column('job_data', Text, nullable=False), # Storing job-specific data as a JSON string
    Column('status', String, default='pending') # e.g., pending, processing, done
)

# Define the settings table for storing API keys and other configurations
settings_table = Table(
    'settings',
    metadata,
    Column('key', String, primary_key=True),
    Column('value', String, nullable=False)
)

# Create tables if they don't exist
metadata.create_all(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Configuration/Settings Functions ---

def save_setting(key, value):
    """Saves a single setting (like an API key) to the database."""
    db_session = SessionLocal()
    try:
        from sqlalchemy.dialects.postgresql import insert
        insert_stmt = insert(settings_table).values(key=key, value=value)
        on_conflict_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['key'],
            set_={'value': value}
        )
        db_session.execute(on_conflict_stmt)
        db_session.commit()
    finally:
        db_session.close()

def get_all_settings():
    """Retrieves all settings from the database and returns them as a dict."""
    db_session = SessionLocal()
    try:
        results = db_session.query(settings_table).all()
        return {row.key: row.value for row in results}
    finally:
        db_session.close()

# --- Caching Functions ---

def cache_data(key, value, ttl):
    db_session = SessionLocal()
    try:
        expiry_time = time.time() + ttl
        serialized_value = json.dumps(value)
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

def add_job_to_queue(chat_id, job_type, job_data):
    """Adds a new job to the Supabase job queue."""
    db_session = SessionLocal()
    try:
        job = {
            "chat_id": str(chat_id),
            "job_type": job_type,
            "job_data": json.dumps(job_data),
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
        return db_session.query(job_queue_table).filter(job_queue_table.c.status == 'pending').all()
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

# --- Data Formatting Utilities ---

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
