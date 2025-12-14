from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, when, count, sum as sum_, max as max_, min as min_,
    collect_list, to_date, concat, lit, current_timestamp, lead, struct, expr, element_at
)
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, TimestampType, DoubleType
)
from pyspark.sql.window import Window
import logging
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from elasticsearch import Elasticsearch, helpers

# ------------------- Logging -------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------- Spark Initialization -------------------
spark = SparkSession.builder \
    .appName("EmployeeKPIRealTime_Daily") \
    .config("spark.sql.streaming.checkpointLocation", "/opt/airflow/checkpoints/kpi_daily4") \
    .getOrCreate()
spark.sparkContext.setLogLevel("WARN")

# ------------------- Kafka Configuration -------------------
KAFKA_BOOTSTRAP_SERVERS = "193.95.30.190:9092"
KAFKA_TOPIC = "logs_event"

# ------------------- Elasticsearch Configuration -------------------
ES_HOST = "193.95.30.190"
ES_PORT = 9200
KPI_INDEX = "employee_kpi_daily_v3"
USERS_INDEX = "users2"

es = Elasticsearch([f"http://{ES_HOST}:{ES_PORT}"])

# ------------------- Schema -------------------
schema = StructType([
    StructField("timestamp", TimestampType(), True),
    StructField("event", StringType(), True),
    StructField("window_name", StringType(), True),
    StructField("application", StringType(), True),
    StructField("control", StringType(), True),
    StructField("text", StringType(), True),
    StructField("employee_id", StringType(), True),
    StructField("session_id", StringType(), True),
    StructField("seq_num", LongType(), True),
    StructField("reason", StringType(), True),
    StructField("idle_id", StringType(), True),
    StructField("duration_minutes", DoubleType(), True),
    StructField("idle_duration_sec", DoubleType(), True),
    StructField("shortcut_name", StringType(), True),
    StructField("status", StringType(), True)
])

# ------------------- Read Kafka Stream -------------------
logger.info("Starting Kafka stream reader...")
raw_df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", "latest") \
    .load()

parsed_df = raw_df.selectExpr("CAST(value AS STRING) as json_str") \
    .withColumn("data", from_json(col("json_str"), schema)) \
    .filter(col("data").isNotNull()) \
    .select("data.*") \
    .filter(col("employee_id").isNotNull())

daily_df = parsed_df.withColumn("date", to_date("timestamp"))

# ------------------- Time Spent per App -------------------
app_window = Window.partitionBy("employee_id", "date").orderBy("timestamp")
app_usage = daily_df.withColumn("next_ts", lead("timestamp").over(app_window)) \
    .withColumn("duration_sec", (col("next_ts").cast("long") - col("timestamp").cast("long"))) \
    .groupBy("employee_id", "date", "application") \
    .agg(sum_("duration_sec").alias("time_spent_sec"))

# ------------------- Daily Aggregation -------------------
daily_agg = daily_df.groupBy("employee_id", "date").agg(
    min_("timestamp").alias("first_event_time"),
    max_("timestamp").alias("last_event_time"),
    sum_(when(col("event") == "idle_end", col("idle_duration_sec")).otherwise(0)).alias("total_idle_today"),
    count(when(col("event") == "pause", 1)).alias("pauses_today"),
    sum_(when(col("event") == "pause", col("duration_minutes")).otherwise(0)).alias("total_pause_minutes_today"),
    count(when(col("event") == "keystrokes", 1)).alias("keystrokes_today"),
    collect_list(struct("event","timestamp")).alias("events_today")
)

daily_agg = daily_agg.withColumn(
    "employee_worked",
    expr("exists(events_today, x -> x.event = 'the user gave their consent to save their activities')")
)

daily_agg = daily_agg.withColumn(
    "active_minutes",
    ((col("last_event_time").cast("long") - col("first_event_time").cast("long"))/60
     - (col("total_idle_today")/60) - col("total_pause_minutes_today"))
)

daily_agg = daily_agg.withColumn(
    "keystrokes_per_minute",
    (col("keystrokes_today") / when(col("active_minutes") > 0, col("active_minutes")).otherwise(1))
)

daily_agg = daily_agg.withColumn(
    "last_event",
    element_at(col("events_today"), -1)
).withColumn(
    "employee_status",
    when(col("last_event.event") == "pause", lit("pause"))
    .when(col("last_event.event").isin("idle", "idle_start", "idle_end"), lit("idle"))
    .when(col("last_event.event").isin("keystrokes", "window_switch", "clipboard_paste", "shortcut", "resume","heartbeat"), lit("active"))
    .when(col("last_event.event") == "keylogger_exit", lit("offline"))
    .otherwise(lit("offline"))
).drop("last_event")

# ------------------- Unique Doc ID -------------------
daily_agg = daily_agg.withColumn(
    "doc_id",
    concat(col("employee_id"), lit("_"), col("date").cast("string"))
).withColumn(
    "es_insert_ts",
    current_timestamp()
)

# ------------------- Write Stream to Elasticsearch via REST API -------------------
def send_to_es(batch_df, batch_id):
    if batch_df.isEmpty():
        return
    
    records = [row.asDict() for row in batch_df.collect()]
    actions = [
        {
            "_index": KPI_INDEX,
            "_id": record["doc_id"],
            "_source": record
        }
        for record in records
    ]

    if actions:
        try:
            helpers.bulk(es, actions)
            logger.info(f"Batch {batch_id}: Inserted {len(actions)} records into ES.")
        except Exception as e:
            logger.error(f"Batch {batch_id}: Failed to insert records into ES: {e}")
            logger.error(f"Records: {records[:5]}")  # log first 5 records for inspection
from pyspark.sql.functions import to_json, col, date_format

daily_agg = daily_agg.withColumn("events_today_json", to_json("events_today")).drop("events_today")
daily_agg = daily_agg.withColumn("date", col("date").cast("string")) \
                     .withColumn("first_event_time", date_format("first_event_time", "yyyy-MM-dd'T'HH:mm:ss")) \
                     .withColumn("last_event_time", date_format("last_event_time", "yyyy-MM-dd'T'HH:mm:ss")) \
                     .withColumn("es_insert_ts", date_format("es_insert_ts", "yyyy-MM-dd'T'HH:mm:ss"))
daily_query = daily_agg.writeStream \
    .foreachBatch(send_to_es) \
    .outputMode("update") \
    .trigger(processingTime="10 seconds") \
    .start()

# ------------------- Await Termination -------------------
try:
    while True:
        now = datetime.now()
        if now.hour >= 23:
            logger.info("Stopping job because it reached 23:00")
            daily_query.stop()
            spark.stop()
            break
        time.sleep(60)
except KeyboardInterrupt:
    logger.info("Stopping streams...")
    daily_query.stop()
    spark.stop()
    logger.info("Streams stopped successfully.")
