import json
import time
import statistics
from kafka import KafkaConsumer
from datetime import datetime, timezone,timedelta  # <-- make sure to import timezone
from dateutil import parser

LATENCIES = []
received_count = 0
start_time = time.time()

consumer = KafkaConsumer(
    "logs_event",
    bootstrap_servers="193.95.30.190:9092",
    auto_offset_reset="latest",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
)

print("🚀 Metrics collector started!")

try:
    for message in consumer:
        event = message.value
        received_count += 1

        # Latency measurement
        if "timestamp" in event:
            try:
                event_ts = parser.isoparse(event["timestamp"])  # detects timezone if present
                if event_ts.tzinfo is None:
                    # assume the timestamp is in local Kafka timezone (e.g., GMT+1)
                    event_ts = event_ts.replace(tzinfo=timezone.utc)  # or use timezone offset
                now = datetime.now(timezone.utc)
                latency = (now - (event_ts - timedelta(hours=1))).total_seconds() * 1000
                LATENCIES.append(latency)
            except Exception as e:
                print("⚠️ Failed to parse timestamp:", event["timestamp"], e)

        # Throughput measurement (every minute)
        if time.time() - start_time >= 60:
            throughput = received_count
            received_count = 0
            duration = round(time.time() - start_time, 3)
            print(f"\n📊 Last Minute Stats:")
            print(f"• Throughput: {throughput} events/min")
            if LATENCIES:
                print(f"• Avg latency: {statistics.mean(LATENCIES):.2f} ms")
                print(f"• p95 latency: {statistics.quantiles(LATENCIES, n=20)[-1]:.2f} ms")
                print(f"• Max latency: {max(LATENCIES):.2f} ms")
            LATENCIES.clear()
            start_time = time.time()

except KeyboardInterrupt:
    print("\n✅ Test stopped by user.")
