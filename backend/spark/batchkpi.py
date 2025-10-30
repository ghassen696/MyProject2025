from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_unixtime,expr, sum, count, length, hour, collect_list, struct, to_date, lit, min as min_, max as max_, row_number, countDistinct, concat_ws,least
)
from pyspark.sql.window import Window
from functools import reduce

# ----------------------------
# Spark Init
# ----------------------------
spark = SparkSession.builder \
    .appName("EmployeeActivityBatchEnhanced") \
    .config("spark.es.nodes.wan.only", "true") \
    .getOrCreate()

# ----------------------------
# Read raw logs from Elasticsearch
# ----------------------------
df = spark.read.format("es") \
    .option("es.nodes", "localhost") \
    .option("es.port", "9200") \
    .option("es.resource", "employee_activity") \
    .load()

df = df.filter(~(
    (col("event") == "keystrokes") & 
    ((length(col("text")) == 0) | col("text").rlike("^<Key.*>$"))
))

from pyspark.sql.functions import when
from pyspark.sql.functions import coalesce

from pyspark.sql.functions import regexp_extract

# Extract application name from window title
# Pattern: last part after last ' - '
df = df.withColumn("app_category",
    when(col("application").rlike("(?i)(vscode|pycharm|intellij|eclipse|sublime|notepad\\+\\+|.*\\.py$|.*\\.exe$)"), "Coding")
    .when(col("application").rlike("(?i)(chrome|firefox|edge|safari|brave)"), "Browsing")
    .when(col("application").rlike("(?i)(slack|teams|zoom|skype|wechat|qq|feishu|ding)"), "Communication")
    .when(col("application").rlike("(?i)(word|excel|powerpoint|wps|onenote|acrobat|pdf)"), "Documentation")
    .when(col("application").rlike("(?i)(outlook|gmail|thunderbird)"), "Email")
    .when(col("application").rlike("(?i)(jira|confluence|trello|asana|notion|clickup)"), "Project Management")
    .when(col("application").rlike("(?i)(vmware|virtualbox|remote desktop|xshell|xftp|putty|securecrt)"), "DevOps / Remote Access")
    .when(col("application").rlike("(?i)(mysql|dbeaver|navicat|datagrip|sql developer)"), "Database Tools")
    .when(col("application").rlike("(?i)(photoshop|illustrator|figma|canva|xd|gimp)"), "Design")
    .when(col("application").rlike("(?i)(huawei cloud|cloud console|obs browser|terraform|ansible|kubectl)"), "Cloud / Infrastructure")
    .when(col("application").rlike("(?i)(youtube|facebook|messenger)"), "Social / Entertainment")
    .otherwise("Other")
).withColumn(
    "subcategory",
    when(col("window").rlike("(?i)(vscode|pycharm|intellij|eclipse|sublime|notepad\\+\\+)"), "IDE")
    .when(col("window").rlike("(?i)(chrome|firefox|edge|safari|brave)"), "Web Browser")
    .when(col("window").rlike("(?i)(slack|teams|zoom|skype|wechat|qq|feishu|ding)"), "Chat / Meetings")
    .when(col("window").rlike("(?i)(word|wps)"), "Word Processor")
    .when(col("window").rlike("(?i)(excel)"), "Spreadsheet")
    .when(col("window").rlike("(?i)(powerpoint)"), "Presentation")
    .when(col("window").rlike("(?i)(acrobat|pdf)"), "PDF Tools")
    .when(col("window").rlike("(?i)(jira|trello|asana|clickup)"), "Task Tracking")
    .when(col("window").rlike("(?i)(confluence|notion)"), "Knowledge Base")
    .when(col("window").rlike("(?i)(vmware|virtualbox|remote desktop)"), "Virtualization / Remote Desktop")
    .when(col("window").rlike("(?i)(xshell|xftp|putty|securecrt)"), "SSH / Terminal Tools")
    .when(col("window").rlike("(?i)(mysql|dbeaver|navicat|datagrip|sql developer)"), "Database Client")
    .when(col("window").rlike("(?i)(photoshop|illustrator|figma|canva|xd|gimp)"), "Design Tools")
    .when(col("window").rlike("(?i)(huawei cloud|cloud console|obs browser)"), "Cloud Console")
    .when(col("window").rlike("(?i)(terraform|ansible|kubectl)"), "Infra-as-Code / CLI")
    .when(col("window").rlike("(?i)(youtube|facebook|messenger)"), "Social Media / Entertainment")
    .otherwise("Other")
)



df = df.withColumn("timestamp", (col("timestamp") / 1000).cast("double"))
df = df.withColumn("timestamp", from_unixtime(col("timestamp")).cast("timestamp"))
# ----------------------------
# Filter logs by day
# ----------------------------
#from pyspark.sql.functions import current_date
#df = df.withColumn("date", to_date(col("timestamp"))).filter(col("date") == current_date())

target_date = "2025-10-22"
df = df.withColumn("date", to_date(col("timestamp"))).filter(col("date") == lit(target_date))

from pyspark.sql.functions import collect_list, struct, sum as sum_

def donut_metrics(df):
    category_usage = df.groupBy("employee_id", "app_category") \
        .agg(count("*").alias("event_count")) \
        .groupBy("employee_id") \
        .agg(
            collect_list(
                struct(
                    col("app_category").alias("category"),
                    col("event_count").alias("count")
                )
            ).alias("donut_chart")
        )
    return category_usage


# ----------------------------
# KPI Functions
# ----------------------------
def typing_metrics(df):
    typing_total = df.filter(col("event") == "keystrokes") \
        .withColumn("char_count", length(col("text"))) \
        .groupBy("employee_id") \
        .agg(sum("char_count").alias("total_keystrokes"))

    typing_hourly = df.filter(col("event") == "keystrokes") \
        .withColumn("char_count", length(col("text"))) \
        .groupBy("employee_id", hour(col("timestamp")).alias("hour")) \
        .agg(sum("char_count").alias("chars_per_hour")) \
        .groupBy("employee_id") \
        .agg(collect_list(struct(col("hour"), col("chars_per_hour"))).alias("typing_per_hour"))
    
    return typing_total, typing_hourly

def idle_metrics(df):
    idle_total = df.filter(col("event") == "idle_end") \
        .groupBy("employee_id") \
        .agg(sum(col("idle_duration_sec")/60).alias("total_idle_min"))
    
    idle_hourly = df.filter(col("event") == "idle_end") \
        .groupBy("employee_id", hour(col("timestamp")).alias("hour")) \
        .agg(sum(col("idle_duration_sec")/60).alias("idle_min_per_hour")) \
        .groupBy("employee_id") \
        .agg(collect_list(struct(col("hour"), col("idle_min_per_hour"))).alias("idle_per_hour"))
    
    idle_per_app = df.filter(col("event") == "idle_end") \
        .groupBy("employee_id", "application") \
        .agg(sum(col("idle_duration_sec")/60).alias("idle_min")) \
        .groupBy("employee_id") \
        .agg(collect_list(struct(col("application"), col("idle_min"))).alias("idle_per_app"))

    return idle_total, idle_hourly, idle_per_app

def pause_metrics(df):
    pause_total = df.filter(col("event") == "pause") \
        .groupBy("employee_id") \
        .agg(count("*").alias("pause_count"), sum("duration_minutes").alias("pause_total_min"))

    pause_hourly = df.filter(col("event") == "pause") \
        .groupBy("employee_id", hour(col("timestamp")).alias("hour"), col("reason")) \
        .agg(count("*").alias("pause_count"), sum("duration_minutes").alias("pause_total_min")) \
        .groupBy("employee_id") \
        .agg(collect_list(struct(col("hour"), col("reason"), col("pause_count"), col("pause_total_min"))).alias("pause_per_hour"))

    avg_pause_duration = df.filter(col("event") == "pause") \
        .groupBy("employee_id") \
        .agg((sum("duration_minutes")/count("*")).alias("avg_pause_duration_min"))
    
    return pause_total, pause_hourly, avg_pause_duration

def shortcut_metrics(df):
    # Aggregate counts per shortcut per employee
    shortcut_total = df.filter(col("event") == "shortcut") \
        .groupBy("employee_id", "shortcut_name") \
        .agg(count("*").alias("count")) \
        .groupBy("employee_id") \
        .agg(
            collect_list(
                struct(
                    col("shortcut_name").alias("shortcut"),
                    col("count").alias("count")
                )
            ).alias("shortcuts_used")
        )

    shortcut_hourly = df.filter(col("event") == "shortcut") \
        .groupBy("employee_id", hour(col("timestamp")).alias("hour"), "shortcut_name") \
        .agg(count("*").alias("count")) \
        .groupBy("employee_id") \
        .agg(
            collect_list(
                struct(
                    col("hour"),
                    col("shortcut_name").alias("shortcut"),
                    col("count")
                )
            ).alias("shortcuts_per_hour")
        )

    return shortcut_total, shortcut_hourly


def heartbeat_metrics(df):
    heartbeat_count = df.filter(col("event") == "heartbeat") \
        .groupBy("employee_id") \
        .agg(count("*").alias("heartbeat_count"))
    return heartbeat_count

def app_metrics(df):
    active_per_app = df.filter(col("event") == "keystrokes") \
        .groupBy("employee_id", "application") \
        .agg(count("*").alias("keystroke_count")) \
        .groupBy("employee_id") \
        .agg(collect_list(struct(col("application"), col("keystroke_count"))).alias("active_per_app"))

    app_hourly = df.filter(col("application").isNotNull()) \
        .groupBy("employee_id", "application", hour(col("timestamp")).alias("hour")) \
        .agg(count("*").alias("events_per_hour")) \
        .groupBy("employee_id") \
        .agg(collect_list(struct("application", "hour", "events_per_hour")).alias("app_usage_per_hour"))

    return active_per_app, app_hourly

def session_metrics(df):
    # Base session start/end
    session_df = df.groupBy("employee_id", "session_id") \
        .agg(
            min_("timestamp").alias("session_start"),
            max_("timestamp").alias("session_end")
        ) \
        .withColumn(
            "session_duration_min",
            (col("session_end").cast("long") - col("session_start").cast("long")) / 60
        )

    # Idle per session
    session_idle = df.filter(col("event") == "idle_end") \
        .groupBy("employee_id", "session_id") \
        .agg(sum(col("idle_duration_sec")/60).alias("idle_min"))

    # Pause per session
    session_pause = df.filter(col("event") == "pause") \
        .groupBy("employee_id", "session_id") \
        .agg(sum("duration_minutes").alias("pause_min"))

    # Merge sessions with idle + pause
    session_summary = session_df.join(session_idle, ["employee_id","session_id"], "left") \
        .join(session_pause, ["employee_id","session_id"], "left") \
        .fillna(0, subset=["idle_min","pause_min"]) \
        .withColumn("active_min", col("session_duration_min") - col("idle_min") - col("pause_min")) \
        .groupBy("employee_id") \
        .agg(
            collect_list(
                struct(
                    "session_id",
                    "session_start",
                    "session_end",
                    "session_duration_min",
                    "active_min",
                    "idle_min",
                    "pause_min"
                )
            ).alias("sessions")
        )

    return session_summary

from pyspark.sql.functions import lag
from pyspark.sql.window import Window

def window_time_metrics(df):
    w = Window.partitionBy("employee_id").orderBy("timestamp")
    
    # Get previous timestamp and window
    df_with_prev = df.filter(col("event") == "window_switch") \
        .withColumn("prev_timestamp", lag("timestamp").over(w)) \
        .withColumn("prev_window", lag("window").over(w)) \
        .withColumn("time_spent_min", (col("timestamp").cast("long") - col("prev_timestamp").cast("long"))/60)
    
    # Aggregate total time per window
    window_time = df_with_prev.groupBy("employee_id", "prev_window") \
        .agg(sum("time_spent_min").alias("time_spent_min")) \
        .groupBy("employee_id") \
        .agg(collect_list(struct(col("prev_window").alias("window"), col("time_spent_min"))).alias("time_per_window"))
    
    return window_time

def window_metrics(df):
    window_counts = df.filter(col("event") == "window_switch") \
        .groupBy("employee_id", "window") \
        .agg(count("*").alias("switch_count"))

    window_rank = window_counts.withColumn("rank", row_number().over(Window.partitionBy("employee_id").orderBy(col("switch_count").desc()))) \
        .filter(col("rank") <= 5) \
        .groupBy("employee_id") \
        .agg(collect_list(struct("window", "switch_count")).alias("top_windows"))

    window_switch_count = df.filter(col("event") == "window_switch") \
        .groupBy("employee_id") \
        .agg(count("*").alias("window_switch_count"))

    return window_rank, window_switch_count

def general_metrics(df):
    # Active vs idle vs pause %
    df_time = df.groupBy("employee_id") \
        .agg(
            sum((col("event") == "idle_end").cast("int")*col("idle_duration_sec")/60).alias("idle_min"),
            sum((col("event") == "pause").cast("int")*col("duration_minutes")).alias("pause_min"),
            ((max_("timestamp").cast("long") - min_("timestamp").cast("long"))/60).alias("total_min")
        ) \
        .withColumn("active_min", col("total_min") - col("idle_min") - col("pause_min")) \
        .withColumn("active_pct", (col("active_min")/col("total_min")*100)) \
        .withColumn("idle_pct", (col("idle_min")/col("total_min")*100)) \
        .withColumn("pause_pct", (col("pause_min")/col("total_min")*100))

    # Keystrokes per active hour (with restricted events)
    keystrokes_per_active_hour = df.groupBy("employee_id", hour(col("timestamp")).alias("hour")) \
        .agg(
            sum((col("event") == "keystrokes").cast("int")).alias("keystrokes"),
        ) \
        .groupBy("employee_id") \
        .agg(collect_list(struct("hour","keystrokes")).alias("keystrokes_per_active_hour"))

    # Unique applications used per day
    unique_apps = df.filter(col("application").isNotNull()) \
        .groupBy("employee_id") \
        .agg(countDistinct("application").alias("unique_apps_count"))

    # Event diversity (normalized)
    event_diversity = df.groupBy("employee_id") \
        .agg(countDistinct("event").alias("distinct_event_types")) \
        .withColumn("event_div_norm", least(col("distinct_event_types")/lit(10), lit(1)))

    # Focus ratio = chars / active minutes
    typing_time = df.filter(col("event") == "keystrokes") \
        .groupBy("employee_id") \
        .agg(sum(length(col("text"))).alias("typing_chars"))
        
    df_time = df_time.join(typing_time, "employee_id", "left") \
        .fillna(0, subset=["typing_chars"]) \
        .withColumn("focus_ratio", col("typing_chars") / (col("active_min")+1))

    # Context switching = window switches / active hours
    window_switches = df.filter(col("event") == "window_switch") \
        .groupBy("employee_id") \
        .agg(count("*").alias("tmp_window_switch_count"))
    df_time = df_time.join(window_switches, "employee_id", "left") \
        .fillna(0, subset=["tmp_window_switch_count"]) \
        .withColumn("context_switch_rate", col("tmp_window_switch_count") / ((col("active_min")/60)+1))\
        .drop("tmp_window_switch_count")

    # Active events restricted
    active_events = df.filter(col("event").isin("keystrokes", "window_switch", "clipboard_paste", "shortcut")) \
        .groupBy("employee_id") \
        .agg(count("*").alias("active_events"))

    return df_time, keystrokes_per_active_hour, unique_apps, event_diversity, active_events

# ----------------------------
# Call all KPI functions
# ----------------------------
dfs = []
dfs.extend(typing_metrics(df))
dfs.extend(idle_metrics(df))
dfs.extend(pause_metrics(df))
dfs.extend(shortcut_metrics(df))
dfs.append(heartbeat_metrics(df))
dfs.extend(app_metrics(df))
dfs.append(session_metrics(df))
dfs.extend(window_metrics(df))
dfs.extend(general_metrics(df))
dfs.append(donut_metrics(df))   # 🔥 Add this
dfs.append(window_time_metrics(df))


# ----------------------------
# Combine all metrics
# ----------------------------
summary_df = reduce(lambda left, right: left.join(right, on="employee_id", how="outer"), dfs)
summary_df = summary_df.withColumn("date", lit(target_date))
summary_df = summary_df.withColumn("doc_id", concat_ws("-", col("employee_id"), col("date")))
from pyspark.sql.functions import greatest, least

summary_df = summary_df \
    .withColumn("focus_norm", least(col("focus_ratio")/5, lit(1))) \
    .withColumn("idle_norm", (100 - col("idle_pct"))/100) \
    .withColumn("context_norm", 1 - least(col("context_switch_rate")/50, lit(1))) \
    .withColumn("event_div_norm", least(col("distinct_event_types")/6, lit(1))) \
    .withColumn("productivity_score",
        ((col("focus_norm")*0.4) +
         (col("idle_norm")*0.3) +
         (col("context_norm")*0.2) +
         (col("event_div_norm")*0.1)) * 100
    )

# ----------------------------
# Write to Elasticsearch
# ----------------------------
summary_df.write.format("es") \
    .option("es.nodes", "localhost") \
    .option("es.port", "9200") \
    .option("es.resource", "employee_kpi_summary4") \
    .option("es.mapping.id", "doc_id") \
    .mode("append") \
    .save()

print(f"✅ Employee activity KPI summary for {target_date} is DONE and saved to Elasticsearch!")
