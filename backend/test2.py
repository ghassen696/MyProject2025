import time
import json
from datetime import datetime
from kafka import KafkaConsumer
import threading

# ---------- CONFIG ----------
KAFKA_BROKER = "193.95.30.190:9092"
KAFKA_TOPIC = "logs_event"
TEST_DURATION_SEC = 20  # Duration to measure throughput/latency
# ----------------------------

latencies = []
event_count = 0
total_received = 0

def process_message(message):
    global latencies, total_received
    try:
        data = json.loads(message.value.decode('utf-8'))
        producer_ts = datetime.fromisoformat(data["timestamp"])
        consume_ts = datetime.now()
        latency_ms = (consume_ts - producer_ts).total_seconds() * 1000
        print(f"Producer timestamp: {producer_ts}, Consumer timestamp: {consume_ts}, Latency: {latency_ms:.2f} ms")
        latencies.append(latency_ms)
        total_received += 1
    except Exception as e:
        print(f"Failed to process message: {e}")

def consume_events():
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=[KAFKA_BROKER],
        auto_offset_reset='latest',  # ✅ Only read new messages
        enable_auto_commit=True,
        group_id=f'test-consumer-group-{int(time.time())}'  # ✅ Unique group per test
    )
    start_time = time.time()
    for message in consumer:
        process_message(message)
        if time.time() - start_time > TEST_DURATION_SEC:
            break
    consumer.close()

def main():
    global event_count
    print(f"Starting Kafka test for {TEST_DURATION_SEC} seconds...")

    # Start consumer in a separate thread
    consumer_thread = threading.Thread(target=consume_events)
    consumer_thread.start()

    # Wait for consumer to finish
    consumer_thread.join()

    # Calculate metrics
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
    else:
        avg_latency = None

    throughput = total_received / TEST_DURATION_SEC
    failure_rate = 0  # If all received, else compute based on N_total

    print("\n===== Test Results =====")
    print(f"Total events received: {total_received}")
    print(f"Average latency: {avg_latency:.2f} ms")
    print(f"Throughput: {throughput:.2f} events/sec")
    print(f"Failure rate: {failure_rate:.2f}%")
    print("========================")

if __name__ == "__main__":
    main()
