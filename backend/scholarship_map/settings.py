from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SM_", env_file=".env", extra="ignore")
    mongo_uri: str = "mongodb://127.0.0.1:27017"
    mongo_database: str = "scholarshipmap"
    kafka_bootstrap: str = "127.0.0.1:9092"
    kafka_topic: str = "scholarships.raw"
    checkpoint_dir: str = "data/checkpoints"
    collector_interval: int = 21600
    request_delay: float = 1.0
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    spark_master: str = "local[2]"
    java_home: str = ""
    spark_packages: str = (
        "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.3,"
        "org.mongodb.spark:mongo-spark-connector_2.13:11.1.0"
    )


def settings() -> Settings:
    return Settings()
