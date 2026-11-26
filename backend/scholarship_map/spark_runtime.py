import os
from pathlib import Path
import sys

from .settings import ROOT, settings


def spark_session(name: str, with_connectors=True):
    # Only process-local environment is changed. A caller can explicitly supply
    # SM_JAVA_HOME; the developer machine's Java 25 is not suitable for Spark 4.0.
    config = settings()
    java_home = config.java_home
    local_java = ROOT / ".runtime" / "java-home.txt"
    if not java_home and local_java.exists():
        java_home = local_java.read_text("utf8").strip()
    if java_home:
        os.environ["JAVA_HOME"] = java_home
    native_home = ROOT / ".runtime" / "hadoop"
    if sys.platform == "win32" and (native_home / "bin" / "winutils.exe").exists():
        os.environ["HADOOP_HOME"] = str(native_home)
        os.environ["PATH"] = str(native_home / "bin") + os.pathsep + os.environ["PATH"]
    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    os.environ["PYTHONPATH"] = str(ROOT / "backend") + os.pathsep + os.environ.get("PYTHONPATH", "")
    import pyspark
    if pyspark.__version__ != "4.0.3":
        raise RuntimeError("Install the pinned Spark dependencies: pip install -e '.[spark]'")
    # A global SPARK_HOME must not silently select another Spark distribution
    # with connectors compiled against a different runtime version.
    os.environ["SPARK_HOME"] = str(Path(pyspark.__file__).parent)
    from pyspark.sql import SparkSession
    builder = (SparkSession.builder.master(config.spark_master).appName(name)
               .config("spark.sql.shuffle.partitions", "2")
               .config("spark.sql.session.timeZone", "UTC")
               .config("spark.driver.bindAddress", "127.0.0.1"))
    if with_connectors:
        builder = (builder.config("spark.jars.packages", config.spark_packages)
                   .config("spark.jars.repositories", "https://repo.maven.apache.org/maven2")
                   .config("spark.mongodb.read.connection.uri", config.mongo_uri)
                   .config("spark.mongodb.write.connection.uri", config.mongo_uri))
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark
