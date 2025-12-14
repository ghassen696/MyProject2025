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
    "daily_batch_jobs",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 20 * * *", 
    catchup=False,
) as dag:

    batchkpi = SSHOperator(
        task_id="batchkpi",
        ssh_conn_id="ssh_vm",
        command=f'''
            export SPARK_HOME={SPARK_HOME} &&
            export PYSPARK_PYTHON={PYSPARK_PYTHON} &&
            cd {BACKEND_PATH} &&
            source venv/bin/activate &&
            spark-submit --packages {SPARK_PACKAGES} spark/batchkpi.py
        '''
    )

    report_pipeline = SSHOperator(
        task_id="report_pipeline",
        ssh_conn_id="ssh_vm",
        command=f'''
            cd {BACKEND_PATH} &&
            source venv/bin/activate &&
            python3 classification/report_pipeline.py
        '''
    )

    build_employeehistory = SSHOperator(
        task_id="build_employeehistory",
        ssh_conn_id="ssh_vm",
        command=f'''
            cd {BACKEND_PATH} &&
            source venv/bin/activate &&
            python3 classification/build_employee_history.py
        '''
    )

    batchkpi >> report_pipeline >> build_employeehistory
