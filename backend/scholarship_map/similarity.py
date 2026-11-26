"""Exact Jaccard reference and genuine Spark MinHash LSH candidate generation."""
import math
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def token_set(text: str) -> set[str]:
    words = [word for word in re.findall(r"[^\W_]+", text.casefold(), re.UNICODE) if len(word) > 1]
    return {" ".join(pair) for pair in zip(words, words[1:])} if len(words) > 1 else set(words)


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def official_identity(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    if not parts.path.strip("/"):
        return None
    query = [(key, value) for key, value in parse_qsl(parts.query) if not key.lower().startswith("utm_")]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(sorted(query)), ""))


def safe_to_merge(left: dict, right: dict) -> bool:
    # LSH similarity alone never establishes identity or destroys a source row.
    url = official_identity(left.get("official_url"))
    return bool(url and url == official_identity(right.get("official_url"))
                and left.get("cycle") and left.get("cycle") == right.get("cycle")
                and left.get("title", "").strip().casefold() == right.get("title", "").strip().casefold())


def exact_pairs(features: dict[str, set[str]], threshold: float) -> set[tuple[str, str]]:
    keys = sorted(features)
    return {(left, right) for index, left in enumerate(keys) for right in keys[index + 1:]
            if jaccard(features[left], features[right]) >= threshold}


def candidate_frame(frame, num_tables=8, threshold=0.65, seed=17):
    from pyspark.ml.feature import CountVectorizer, MinHashLSH
    from pyspark.sql import functions as F
    from pyspark.sql.types import ArrayType, StringType
    if not 0 < threshold <= 1 or not 1 <= num_tables <= 128:
        raise ValueError("Invalid LSH parameters")
    tokenize = F.udf(lambda text: sorted(token_set(text or "")), ArrayType(StringType()))
    prepared = frame.withColumn("tokens", tokenize(F.concat_ws(" ", "title", "provider", "description")))
    prepared = prepared.filter(F.size("tokens") > 0)
    count = prepared.count()
    if not count:
        return None, None, {"records": 0, "vocabulary_size": 0}
    vectorizer = CountVectorizer(inputCol="tokens", outputCol="features", binary=True, minDF=1.0,
                                vocabSize=1 << 20).fit(prepared)
    features = vectorizer.transform(prepared)
    model = MinHashLSH(inputCol="features", outputCol="hashes", numHashTables=num_tables, seed=seed).fit(features)
    hashed = model.transform(features).cache()
    hashed.count()
    joined = model.approxSimilarityJoin(hashed, hashed, math.nextafter(1.0 - threshold, 1.0),
                                       distCol="feature_distance")
    pairs = (joined.filter(F.col("datasetA.id") < F.col("datasetB.id"))
             .select(F.col("datasetA.id").alias("left_id"), F.col("datasetB.id").alias("right_id"),
                     F.col("datasetA.tokens").alias("left_tokens"), F.col("datasetB.tokens").alias("right_tokens"),
                     F.col("datasetA.title").alias("left_title"), F.col("datasetB.title").alias("right_title"),
                     F.col("datasetA.official_url").alias("left_url"), F.col("datasetB.official_url").alias("right_url"),
                     F.col("datasetA.cycle").alias("left_cycle"), F.col("datasetB.cycle").alias("right_cycle"))
             .withColumn("jaccard", F.size(F.array_intersect("left_tokens", "right_tokens")) /
                         F.size(F.array_union("left_tokens", "right_tokens")))
             .filter(F.col("jaccard") >= threshold))
    return pairs, hashed, {"records": count, "vocabulary_size": len(vectorizer.vocabulary),
                            "num_hash_tables": num_tables, "seed": seed, "similarity_threshold": threshold}
