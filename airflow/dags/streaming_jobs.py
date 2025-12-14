from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

BACKEND_PATH = "/root/PFE_Project_LatestV/backend"
SPARK_PACKAGES = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1,org.elasticsearch:elasticsearch-spark-30_2.12:9.0.0"
SPARK_HOME = "/root/spark"
PYSPARK_PYTHON = f"{BACKEND_PATH}/venv/bin/python"

with DAG(
    "streaming_jobs",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,  
    catchup=False,
) as dag:

    rawbatch_stream = SSHOperator(
        task_id="rawbatch_stream",
        ssh_conn_id="ssh_vm",
        command=f'''
            export SPARK_HOME={SPARK_HOME} &&
            export PYSPARK_PYTHON={PYSPARK_PYTHON} &&
            cd {BACKEND_PATH} &&
            source venv/bin/activate &&
            spark-submit --packages {SPARK_PACKAGES} spark/Rawbatch.py
        '''
    )

    realtimekpi_stream = SSHOperator(
        task_id="realtimekpi_stream",
        ssh_conn_id="ssh_vm",
        command=f'''
            export SPARK_HOME={SPARK_HOME} &&
            export PYSPARK_PYTHON={PYSPARK_PYTHON} &&
            cd {BACKEND_PATH} &&
            source venv/bin/activate &&
            spark-submit --packages {SPARK_PACKAGES} spark/realtimekpi2testoriginal.py
        '''
    )

    # Both streaming jobs run in parallel
    [rawbatch_stream, realtimekpi_stream]
