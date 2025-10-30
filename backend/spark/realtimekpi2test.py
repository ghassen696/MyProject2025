from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, when, count, sum as sum_, max as max_, min as min_,
    collect_list, to_date, concat, lit, current_timestamp, array_contains,
    lead,struct,array_contains,expr
)
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, TimestampType, DoubleType
)
from pyspark.sql.window import Window
import logging

from pyspark.sql.window import Window
import logging
import smtplib
from email.mime.text import MIMEText
# ------------------- Logging -------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------- Spark Initialization -------------------
spark = SparkSession.builder \
    .appName("EmployeeKPIRealTime_Daily") \
    .config("spark.sql.streaming.checkpointLocation", "/root/AI-PFE/checkpoints/kpi_daily4") \
    .config("spark.es.nodes.wan.only", "true") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# ------------------- Kafka Configuration -------------------
KAFKA_BOOTSTRAP_SERVERS = "193.95.30.190:9092"
KAFKA_TOPIC = "logs_event"

# ------------------- Elasticsearch Configuration -------------------
ES_HOST = "localhost"
ES_PORT = "9200"
KPI_INDEX = "employee_kpi_daily_v3"

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
    .option("startingOffsets", "earliest") \
    .load()

parsed_df = raw_df.selectExpr("CAST(value AS STRING) as json_str") \
    .withColumn("data", from_json(col("json_str"), schema)) \
    .filter(col("data").isNotNull()) \
    .select("data.*") \
    .filter(col("employee_id").isNotNull())

# ------------------- Filter Activity Events -------------------
activity_events = ["keystrokes", "window_switch", "clipboard_paste", "shortcut", "pause", "resume", "idle_start", "idle_end", "heartbeat"]
clean_df = parsed_df.filter(col("event").isin(activity_events))

# Add date
daily_df = clean_df.withColumn("date", to_date("timestamp"))

# ------------------- Time Spent per App -------------------
app_window = Window.partitionBy("employee_id", "date").orderBy("timestamp")

app_usage = daily_df \
    .withColumn("next_ts", lead("timestamp").over(app_window)) \
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
#--------------------ComputeConsent-----------------
daily_agg = daily_agg.withColumn(
    "employee_worked",
    expr("""
        exists(events_today, x -> x.event = 'the user gave their consent to save their activities')
    """)
)
# ------------------- Compute KPIs -------------------
daily_agg = daily_agg.withColumn(
    "active_minutes",
    ((col("last_event_time").cast("long") - col("first_event_time").cast("long"))/60
     - (col("total_idle_today")/60) - col("total_pause_minutes_today"))
)

daily_agg = daily_agg.withColumn(
    "keystrokes_per_minute",
    (col("keystrokes_today") / when(col("active_minutes") > 0, col("active_minutes")).otherwise(1))
)

# ------------------- Status Logic -------------------
from pyspark.sql.functions import element_at, size

daily_agg = daily_agg.withColumn(
    "last_event",
    element_at(col("events_today"), -1)
).withColumn(
    "employee_status",
    when(col("last_event.event") == "pause", lit("pause"))
    .when(col("last_event.event").isin("idle", "idle_start", "idle_end"), lit("idle"))
    .when(col("last_event.event").isin(
        "keystrokes", "window_switch", "clipboard_paste", "shortcut", "resume"
    ), lit("active"))
    .when(col("last_event.event") == "keylogger_exit", lit("offline"))
    .otherwise(lit("offline"))
).drop("last_event")
#---------------------loading mails------------------
users_df = spark.read.format("es") \
    .option("es.nodes", ES_HOST) \
    .option("es.port", ES_PORT) \
    .option("es.resource", "users2") \
    .load() \
    .select("employee_id", "email")
# -------------------- Heartbeat Monitoring ----------------------
from pyspark.sql.functions import unix_timestamp, current_timestamp

# Extract last heartbeat per employee
heartbeat_df = clean_df.filter(col("event") == "heartbeat") \
    .groupBy("employee_id") \
    .agg(max_("timestamp").alias("last_heartbeat"))

# Join with static user emails
heartbeat_with_email = heartbeat_df.join(users_df, on="employee_id", how="left")

# Compute seconds since last heartbeat
heartbeat_with_email = heartbeat_with_email.withColumn(
    "seconds_since_last_heartbeat",
    when(col("last_heartbeat").isNotNull(),
         unix_timestamp(expr("current_timestamp()")) - unix_timestamp(col("last_heartbeat"))
    ).otherwise(999999)
)


# Filter employees missing heartbeat for more than 2 minutes 
missing_heartbeat_df = heartbeat_with_email.filter(col("seconds_since_last_heartbeat") > 120)

# ------------------- Email Sending -------------------
def send_alert_email(email, employee_id, last_heartbeat):
    msg = MIMEText(f"Employee {employee_id} missing heartbeat since {last_heartbeat}")
    msg['Subject'] = f"⚠️ Missing Heartbeat Alert for {employee_id}"
    msg['From'] = "huaweitesttest1@gmail.com"
    msg['To'] = email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login("huaweitesttest1@gmail.com", "ordf ylso cjkm koiq")
            server.send_message(msg)
        logger.info(f"✅ Alert sent for {employee_id} to {email}")
    except Exception as e:
        logger.error(f"❌ Failed to send email to {email}: {e}")

"""# foreachBatch: check each micro-batch
def notify_missing_heartbeat(batch_df, batch_id):
    from pyspark.sql.functions import unix_timestamp, current_timestamp, expr, col, when

    if batch_df.isEmpty():
        logger.info("⚠️ Empty batch, skipping.")
        return

    # Recalculate dynamically per batch
    updated_df = batch_df.withColumn(
        "seconds_since_last_heartbeat",
        when(col("last_heartbeat").isNotNull(),
             unix_timestamp(expr("current_timestamp()")) - unix_timestamp(col("last_heartbeat"))
        ).otherwise(999999)
    )

    filtered = updated_df.filter(col("seconds_since_last_heartbeat") > 30)
    count_missing = filtered.count()
    logger.info(f"Batch {batch_id}: {count_missing} missing heartbeat employees")

    for row in filtered.collect():
        if row.email:
            send_alert_email(row.email, row.employee_id, row.last_heartbeat)
        else:
            logger.warning(f"No email for {row.employee_id}")


# Stream to trigger alerts every minute
heartbeat_query = missing_heartbeat_df.writeStream \
    .foreachBatch(notify_missing_heartbeat) \
    .outputMode("update") \
    .trigger(processingTime="60 seconds") \
    .start()

"""
# ------------------- Unique Doc ID -------------------
daily_agg = daily_agg.withColumn(
    "doc_id",
    concat(col("employee_id"), lit("_"), col("date").cast("string"))
)

# ------------------- Write Stream -------------------
logger.info("Starting daily KPI stream to Elasticsearch...")
daily_query = daily_agg.writeStream \
    .format("es") \
    .option("es.nodes", ES_HOST) \
    .option("es.port", ES_PORT) \
    .option("es.resource", KPI_INDEX) \
    .option("es.mapping.id", "doc_id") \
    .outputMode("update") \
    .trigger(processingTime="10 seconds") \
    .start()

# ------------------- Await Termination -------------------
try:
    spark.streams.awaitAnyTermination()
except KeyboardInterrupt:
    logger.info("Stopping streams...")
    daily_query.stop()
    spark.stop()
    logger.info("Streams stopped successfully.")
