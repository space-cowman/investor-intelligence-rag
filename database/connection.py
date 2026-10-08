import os
import time
from functools import lru_cache

import boto3
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

load_dotenv()


def _iam_token() -> str:
    """Short-lived login token generated from your AWS credentials."""
    return boto3.client("rds", region_name=os.getenv("AWS_REGION", "us-east-1")).generate_db_auth_token(
        DBHostname=os.environ["DB_HOST"],
        Port=int(os.getenv("DB_PORT", "5432")),
        DBUsername=os.getenv("DB_USER", "postgres"),
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """One shared SQLAlchemy engine; a fresh IAM token is used for every new connection."""
    url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("DB_USER", "postgres"),
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "postgres"),
    )
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"sslmode": "require", "connect_timeout": 30},
    )

    @event.listens_for(engine, "do_connect")
    def _inject_token(dialect, conn_rec, cargs, cparams):
        cparams["password"] = _iam_token()

    return engine


def wait_for_db(retries: int = 6, delay: int = 10) -> None:
    """Retry while Aurora Serverless v2 resumes from auto-pause."""
    for attempt in range(1, retries + 1):
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError as e:
            print(f"Database not ready (attempt {attempt}/{retries}); it may be resuming: {e.__class__.__name__}")
            time.sleep(delay)
    raise RuntimeError("Could not connect to the database. Check DB_HOST and IAM permissions.")