import awswrangler as wr
from pg8000.native import Connection, InterfaceError
import logging
import boto3
from botocore.exceptions import ClientError
import json
import os

# create logger to log in to cloudeWatch
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    AWS Lambda handler to load Parquet files from S3 into a PostgreSQL data warehouse.

    This function:
    - Extracts a timestamp from the event to determine which data files to load.
    - Retrieves database credentials from AWS Secrets Manager.
    - Reads multiple Parquet files from a processed S3 bucket.
    - Loads the data into corresponding tables in the warehouse using AWS Data Wrangler and SQLAlchemy.

    Args:
        event (dict): Event payload containing 'myresult.timestamp_to_transform' key for filtering data.
        context (LambdaContext): AWS Lambda context object (not used but required by AWS Lambda).

    Returns:
        dict: Contains the HTTP status code, the timestamp used, and the number of tables successfully updated.
    """

    # Get timestamp from event
    last_checked = event['myresult']['timestamp_to_transform']
    # print(json.dumps(event, indent=2))

    # Get processed S3 bucket from enviorment
    processed_bucket = os.getenv('S3_PROCESSED_BUCKET')
    
    # Create sm_client for secret manager
    sm_client=boto3.client("secretsmanager")

    tables = [
        "fact_sales_order",
        "fact_purchase_order",
        "fact_payment",
        "dim_currency", 
        "dim_location",
        "dim_design",
        "dim_staff",
        "dim_counterparty", 
        "dim_date",
        "dim_transaction",
        "dim_payment_type"
    ]

    # Get credentials and create db connection
    w_creds = get_w_creds(sm_client)
    db_conn = create_db_connection(w_creds)

    tables_loaded = 0

    # Process and load tables
    for table in tables:
        # define parquet file path from prossed S3 bucket
        file_key = f"{table}/{last_checked}.parquet"
        file_path_s3 = f"s3://{processed_bucket}/{file_key}"

        if not check_file_exists_in_processed_bucket(processed_bucket, file_key):
            logger.warning(f"No new data found to {table} table. File not found: {file_key}")
            continue

        try:
            # read the parquet Dataframe
            df = wr.s3.read_parquet(file_path_s3)
            logger.info(f"File {file_path_s3} read successfully from S3 bucket.")
            
            # Load DataFrame into PostgreSQL
            wr.postgresql.to_sql(
                df=df,
                table=table,
                schema="public",
                con=db_conn,
                mode="append",
                use_column_names=True
            )

            tables_loaded += 1
            logger.info(f"Loaded {table} table to warehouse.")

        except Exception as e:
            logger.error(f"Error occured for processing table: {table}: {str(e)}.")
            raise {str(e)}

    # Return status and how many tables were loaded
    return {
        "statusCode" : 200, 
        "timestamp_to_load": last_checked, 
        "numberOfTablesUpdated" : tables_loaded
        }

# get warehouse credentials from aws secret manager   
def get_w_creds(sm_client):
    """
    Fetches database credentials from AWS Secrets Manager.

    Args:
        sm_client: Boto3 SecretsManager client.

    Returns:
        dict: A dictionary containing database credentials with keys:
            WAREHOUSE_USER, WAREHOUSE_PASSWORD, WAREHOUSE_HOST,
            WAREHOUSE_PORT, WAREHOUSE_NAME
    """
    try:
        response = sm_client.get_secret_value(SecretId='warehouse_secrets')
        warehouse_credentials = json.loads(response["SecretString"])
        return warehouse_credentials

    except sm_client.exceptions.ResourceNotFoundException as par_not_found_error:
        logger.error(f"get_last_checked: The parameter was not found: {str(par_not_found_error)}")
        raise par_not_found_error
    except ClientError as error:
        logger.error(f"get_last_checked: There has been an error: {str(error)}")
        raise error


def create_db_connection(w_creds):
    """ Summary:
    Connect to the warehouse database using credentials fetched from 
    AWS Secret Manager. Uses Connection module from pg8000.native library 

    Return Connection
    """
    try:
        return Connection(
            user = w_creds["WAREHOUSE_USER"],
            password = w_creds["WAREHOUSE_PASSWORD"],
            database = w_creds["WAREHOUSE_DATABASE"],
            host = w_creds["WAREHOUSE_HOST"],
            port = w_creds["WAREHOUSE_PORT"]
        )
    except InterfaceError as interface_error:
        logger.error(f"create_db_connection: cannot connect to database: {interface_error}")
        raise interface_error
    except Exception as error:
        logger.error(f"create_db_connection: there has been an error: {str(error)}")
        raise error
    

def check_file_exists_in_processed_bucket(bucket, file_key):
    """
    Summary:
    Check whether the file exist in the S3 processed bucket
    If exist return True, False if not exist, as there is case it might no new data added at that at that last_checked time, other case throw error.
    """
    s3_client = boto3.client("s3")

    try:
        s3_client.head_object(Bucket=bucket, Key=file_key)
        logger.info(f"File key found in S3 bucket: {file_key}")
        return True
    
    except ClientError as error:
        if error.response["Error"]["Code"] == "404":
            logger.info(f"Key: '{file_key}' does not exist!")
            return False
        
        elif error.response['Error']['Code'] == 'NoSuchBucket':
            logger.error(f"Bucket: {bucket} does not exist!")
            raise error
        else:
            logger.error(f"Unexpected error occurred during checking file exist: {str(error)}")
            raise error