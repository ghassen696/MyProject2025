from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, current_timestamp, unix_timestamp
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, DoubleType
import pandas as pd
import os

# ------------------- Spark Initialization -------------------
spark = SparkSession.builder \
    .appName("EmployeeKPIRealTime_Test") \
    .getOrCreate()
spark.sparkContext.setLogLevel("WARN")

# ------------------- Kafka Configuration -------------------
KAFKA_BOOTSTRAP_SERVERS = "193.95.30.190:9092"
KAFKA_TOPIC = "logs_event"

# ------------------- Schema -------------------
schema = StructType([
    StructField("timestamp", TimestampType(), True),
    StructField("event", StringType(), True),
    StructField("employee_id", StringType(), True),
    StructField("session_id", StringType(), True),
    StructField("seq_num", StringType(), True),
    StructField("duration_minutes", DoubleType(), True),
    StructField("idle_duration_sec", DoubleType(), True)
])

# ------------------- Read Kafka Stream -------------------
raw_df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", "latest") \
    .load()

parsed_df = raw_df.selectExpr("CAST(value AS STRING) as json_str") \
    .withColumn("data", from_json(col("json_str"), schema)) \
    .select("data.*") \
    .filter(col("employee_id").isNotNull())

# ------------------- Compute Latency -------------------
latency_df = parsed_df.withColumn(
    "latency_sec",
    unix_timestamp(current_timestamp()) - unix_timestamp(col("timestamp"))
)

# ------------------- Prepare CSV storage -------------------
metrics_file = "spark_metrics.csv"
# Create CSV with header if not exists
if not os.path.exists(metrics_file):
    pd.DataFrame(columns=[
        "batch_id", "total_events", "avg_latency_sec",
        "keystrokes_count", "idle_events_count"
    ]).to_csv(metrics_file, index=False)

# ------------------- Aggregate Metrics per Micro-batch -------------------
def compute_metrics(batch_df, batch_id):
    if batch_df.isEmpty():
        print(f"Batch {batch_id}: no events")
        return
    
    total_events = batch_df.count()
    avg_latency = batch_df.agg({"latency_sec": "avg"}).collect()[0][0]
    keystrokes_count = batch_df.filter(col("event") == "keystrokes").count()
    idle_events = batch_df.filter(col("event").isin("idle_start", "idle_end")).count()
    
    print(f"Batch {batch_id}: Total events={total_events}, Avg latency={avg_latency:.2f}s, Keystrokes={keystrokes_count}, Idle={idle_events}")
    
    # Save to CSV
    df = pd.DataFrame([{
        "batch_id": batch_id,
        "total_events": total_events,
        "avg_latency_sec": avg_latency,
        "keystrokes_count": keystrokes_count,
        "idle_events_count": idle_events
    }])
    df.to_csv(metrics_file, mode="a", header=False, index=False)

# ------------------- Start Streaming -------------------
query = latency_df.writeStream \
    .foreachBatch(compute_metrics) \
    .outputMode("update") \
    .trigger(processingTime="10 seconds") \
    .start()

# ------------------- Run for a Fixed Duration (30 min) -------------------
try:
    query.awaitTermination(timeout=30*60)  # 30 minutes
except KeyboardInterrupt:
    print("Stopping test...")
finally:
    query.stop()
    spark.stop()
    print(f"Metrics saved to {metrics_file}")
