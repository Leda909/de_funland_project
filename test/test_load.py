from src.lambda_handler.load import lambda_handler, get_w_creds, create_db_connection, check_file_exists_in_processed_bucket
import awswrangler as wr
from pg8000.native import Connection, InterfaceError
import boto3
import pandas as pd
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from moto import mock_aws
from datetime import date, time
from dotenv import load_dotenv


# ----------
# Fixtures
# ----------

@pytest.fixture(autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"

@pytest.fixture(scope="function")
def sm_client():
    with mock_aws():
        sm_client = boto3.client("secretsmanager", region_name="eu-west-2")
        yield sm_client

@pytest.fixture(scope="function")
def s3_client():
    with mock_aws():
        s3_client = boto3.client("s3", region_name = "eu-west-2")
        yield s3_client    

# ---------------------------------------------
# Fixtures that populates parquet files from processed test_bucket
# ---------------------------------------------
    
@pytest.fixture(scope="function")
def processed_bucket_with_parquet_files(s3_client):
    """
    Creates the processed test_bucket and add one - one row parquet files
    in a structure and values that matches what the transform lambda produced.
    """
    with mock_aws():
        test_bucket = 'processed-test_bucket'

        s3_client.create_bucket(
                Bucket=test_bucket,
                CreateBucketConfiguration={
                    "LocationConstraint" : "eu-west-2"
                }
            )
        file_marker = "1995-01-01 00:00:00.000000"

        os.environ["S3_PROCESSED_BUCKET"] = test_bucket

        # ---------- fact_sales_order ----------
        wr.s3.to_parquet(
            df=pd.DataFrame(
                [[ 2, 2, date(2022, 11, 3), time(14, 20, 52, 186000), date(2022, 11, 3), time(14, 20, 52, 186000), 19, 8, 42972, 3.94, 2, 3, date(2022, 11, 8), date(2022, 11, 7), 8 ]],
                columns=[ "sales_record_id", "sales_order_id", "created_date", "created_time", "last_updated_date", "last_updated_time", "sales_staff_id", "counterparty_id", "units_sold", "unit_price", "currency_id", "design_id", "agreed_payment_date", "agreed_delivery_date", "agreed_delivery_location_id", ]
            ),
            path=f"s3://{test_bucket}/fact_sales_order/{file_marker}.parquet",
            index=False,
        )

        # ----------- dim_currency ------------
        wr.s3.to_parquet(
            df=pd.DataFrame(
                [[1, "GBP", "Pounds"]],
                columns = ["currency_id", "currency_code", "currency_name"]
                ),
                path=f"s3://{test_bucket}/dim_currency/{file_marker}.parquet",
                index=False,
            )
        
        # ---------- dim_location ----------
        wr.s3.to_parquet(
            df=pd.DataFrame(
                [[ 1, "6826 Herzog Via", None, "Avon", "New Patienceburgh", "28441", "Turkey", "1803 637401"]],
                columns=["location_id", "address_line_1", "address_line_2", "district", "city", "postal_code", "country", "phone"],
            ),
            path=f"s3://{test_bucket}/dim_location/{file_marker}.parquet",
            index=False,
        )
        
        # ----------- dim_design ------------
        wr.s3.to_parquet(
            df=pd.DataFrame(
                [[0, "Wooden", "/usr", "wooden-20220717-npgz.json"]],
                columns=["design_id", "design_name", "file_location", "file_name"]
                ),
                path=f"s3://{test_bucket}/dim_design/{file_marker}.parquet",
                index=False,
            )
        
        # ----------- dim_staff ------------
        wr.s3.to_parquet(
            df=pd.DataFrame(
                [[ 1, "Jeremie", "Franey", "Purchasing", "Manchester", "jeremie.franey@terrifictotes.com"]],
                columns=["staff_id", "first_name", "last_name", "department_name", "location", "email_address",]
                ),
                path=f"s3://{test_bucket}/dim_staff/{file_marker}.parquet",
                index=False,
            )

        # ---------- dim_counterparty ----------
        wr.s3.to_parquet(
            df=pd.DataFrame(
                [[ 1, "Fahey and Sons", "605 Haskell Trafficway", "Axel Freeway", "East Bobbie", "Heard Island and McDonald Islands", None, "9687 937447", "88253-4257" ]],
                columns=["counterparty_id", "counterparty_legal_name", "counterparty_legal_address_line_1", "counterparty_legal_address_line_2", "counterparty_legal_district", "counterparty_legal_city", "counterparty_legal_postal_code", "counterparty_legal_country", "counterparty_legal_phone_number" ],
            ),
            path=f"s3://{test_bucket}/dim_counterparty/{file_marker}.parquet",
            index=False,
        )

        # ---------- dim_date ----------
        wr.s3.to_parquet(
            df=pd.DataFrame(
                [[pd.Timestamp("2022-11-10"), 2022, 11, 10, 3, "Thursday", "November", 4 ]],
                columns=["date_id", "year", "month", "day", "day_of_week", "day_name", "month_name", "quarter"],
            ),
            path=f"s3://{test_bucket}/dim_date/{file_marker}.parquet",
            index=False,
        )

        yield test_bucket, file_marker


#-------------- Test Lambda Handler -------------------
        
class TestLambdaHandler:
    def test_happy_path_loads_everything(self, s3_client, sm_client, processed_bucket_with_parquet_files):
        # Arrange
        test_bucket, file_marker = processed_bucket_with_parquet_files

        # Mock the event data
        test_event = {
            "myresult": {
                "timestamp_to_transform": file_marker
            }
        }

        with patch('src.lambda_handler.load.get_w_creds') as mock_get_creds, \
            patch('src.lambda_handler.load.create_db_connection') as mock_create_conn, \
            patch('awswrangler.s3.read_parquet') as mock_read_parquet, \
            patch('awswrangler.postgresql.to_sql') as mock_to_sql:
      
            # Setup mock return values
            mock_get_creds.return_value = {
                "WAREHOUSE_USER": "test",
                "WAREHOUSE_PASSWORD": "test",
                "WAREHOUSE_HOST": "test",
                "WAREHOUSE_PORT": "5432",
                "WAREHOUSE_DATABASE": "test"
            }
            mock_create_conn.return_value = MagicMock()
            
            # Mock read_parquet to return a dummy DataFrame
            mock_read_parquet.return_value = pd.DataFrame({'dummy': [1]})
            
            # Mock to_sql to succeed
            mock_to_sql.return_value = True

            # Act
            response = lambda_handler(test_event, {})

            # Assert
            assert response["statusCode"] == 200
            assert response["numberOfTablesUpdated"] == 7


#-------------- Test Get Warehouse Credentials ---------------

@mock_aws            
class TestGetWarehouseCredentials:
    # helper function to validate missed db keys
    REQUIRED_KEYS = [
        "WAREHOUSE_USER",
        "WAREHOUSE_PASSWORD",
        "WAREHOUSE_HOST",
        "WAREHOUSE_PORT",
        "WAREHOUSE_DATABASE"
    ]
    
    def validate_db_credentials(self, creds):
        """ Dummy validator function used only in test. """
        missing_keys = [k for k in self.REQUIRED_KEYS if k not in creds]

        if missing_keys:
            raise KeyError(f"Missing required keys in secret: {', '.join(missing_keys)}.")

    def test_returns_dict_when_secret_exists(self, sm_client):
        test_secret_dict = {
            "WAREHOUSE_USER": "user",
            "WAREHOUSE_PASSWORD": "pass",
            "WAREHOUSE_HOST": "host",
            "WAREHOUSE_PORT": "port",
            "WAREHOUSE_DATABASE": "test_db"
        }

        sm_client.create_secret(
            Name="warehouse_secrets",
            SecretString=json.dumps(test_secret_dict)
            # SecretString=test_secret_dict
        )

        assert get_w_creds(sm_client) == test_secret_dict

    def test_get_db_credentials_raises_when_missing_key(self, sm_client):
        test_secret_dict = {
            "WAREHOUSE_USER": "user",
            "WAREHOUSE_PASSWORD": "pass",
            "WAREHOUSE_DATABASE": "test_db"
        }

        sm_client.get_secret_value = MagicMock(
            return_value={"SecretString": json.dumps(test_secret_dict)}
        )

        # get the credential dict from the mocked secret string
        creds = json.loads(sm_client.get_secret_value()['SecretString'])

        with pytest.raises(KeyError, match="Missing required keys in secret: WAREHOUSE_HOST, WAREHOUSE_PORT"):
            self.validate_db_credentials(creds)

    def test_raises_when_secret_missing(self, sm_client):
        sm_client.get_secret_value = MagicMock(
            side_effect=sm_client.exceptions.ResourceNotFoundException(
                {"Error": {"Code": "ResourceNotFoundException"}}, "GetSecretValue"
            )
        )

        with pytest.raises(sm_client.exceptions.ResourceNotFoundException):
            get_w_creds(sm_client)

    def test_raises_on_client_error(self, sm_client):
        sm_client.get_secret_value = MagicMock(
            side_effect=ClientError(
                {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}}, "GetSecretValue"
            )
        )

        with pytest.raises(ClientError, match="Access denied"):
            get_w_creds(sm_client)

    def test_db_credentials_match_env(self, sm_client):
        """
        Test that asserts the DB credentials returned by get_w_creds 
        match those defined in the .env file.
        """
        load_dotenv()

        # prepare expected credentials from .env
        expected_creds = {
            "WAREHOUSE_USER": os.getenv("warehouse_user"),
            "WAREHOUSE_PASSWORD": os.getenv("warehouse_password"),
            "WAREHOUSE_HOST": os.getenv("warehouse_host"),
            "WAREHOUSE_PORT": os.getenv("warehouse_port"),
            "WAREHOUSE_DATABASE": os.getenv("warehouse_database")
        }

        # create secret in mock Secrets Manager with same credentials
        sm_client.create_secret(
            Name="warehouse_secrets",
            SecretString=json.dumps(expected_creds)
        )

        # fetch credentials using get_w_creds
        returned_creds = get_w_creds(sm_client)

        # assert returned credentials match expected
        assert returned_creds == expected_creds


#-------------- Test Create DB Connection ---------------
            
class TestCreateDbConnection:
    def test_returns_connection_with_correct_credentials(self):
        creds = {
            "WAREHOUSE_USER": "user",
            "WAREHOUSE_PASSWORD": "pass",
            "WAREHOUSE_HOST": "localhost",
            "WAREHOUSE_PORT": "5432",
            "WAREHOUSE_DATABASE": "db"
        }
        
        with patch('src.lambda_handler.load.Connection') as mock_conn:
            # create mock connection object with the expected attributes
            mock_connection = MagicMock()
            mock_connection.user = "user"
            mock_connection.password = "pass"
            mock_connection.database = "db"
            mock_connection.host = "localhost"
            mock_connection.port = "5432"
            
            # configure the mock to return mock conn
            mock_conn.return_value = mock_connection
            
            # call the function
            connection = create_db_connection(creds)
            
            # verify the connection was created with correct params
            mock_conn.assert_called_once_with(
                user="user",
                password="pass",
                host="localhost",
                database="db",
                port="5432"
            )
            
            # assert returned connection has correct attributes
            assert connection.user == "user"
            assert connection.password == "pass"
            assert connection.database == "db"
            assert connection.host == "localhost"
            assert connection.port == "5432"

    def test_raises_interface_error_on_connection_failure(self):
        creds = {
            "WAREHOUSE_USER": "user",
            "WAREHOUSE_PASSWORD": "pass",
            "WAREHOUSE_HOST": "localhost",
            "WAREHOUSE_PORT": "5432",
            "WAREHOUSE_DATABASE": "db"
        }
        
        with patch('src.lambda_handler.load.Connection') as mock_conn:
            # make the Connection raise an InterfaceError
            mock_conn.side_effect = InterfaceError("Connection failed")
            
            with pytest.raises(InterfaceError, match="Connection failed"):
                create_db_connection(creds)
            
            # verify Connection was called with correct params
            mock_conn.assert_called_once_with(
                user="user",
                password="pass",
                host="localhost",
                database="db",
                port="5432"
            )


#-------------- Test Check File Exists in Processed Bucket ---------------

class TestCheckFileExistsInProcessedBucket:
    def test_returns_true_when_file_exists(self, s3_client):
        test_bucket = "test-bucket-processed"
        test_key = "test-file.parquet"
        
        s3_client.create_bucket(
            Bucket=test_bucket,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
        )

        s3_client.put_object(Bucket=test_bucket, Key=test_key, Body="test")
        
        assert check_file_exists_in_processed_bucket(test_bucket, test_key) is True

    def test_returns_false_when_file_not_found(self, s3_client):
        test_bucket = "test-bucket-processed"
        test_key = "non-existent-file.parquet"
        
        s3_client.create_bucket(
            Bucket=test_bucket,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
        )
        
        assert check_file_exists_in_processed_bucket(test_bucket, test_key) is False

    def test_raise_error_when_bucket_not_found(self, s3_client):
        test_bucket = "non-existent-bucket"
        test_key = "test-file.parquet"

        sm_client.head_object = MagicMock(
            side_effect=ClientError(
                {"Error": {"Code": "NoSuchBucket"}}, "HeadObject"
            )
        )

        with pytest.raises(ClientError) as exc_info:
            check_file_exists_in_processed_bucket(test_bucket, test_key)

        assert exc_info.value.response['Error']['Code'] == 'NoSuchBucket'


    def test_raises_client_error_for_other_errors(self, s3_client):
        test_bucket = "test-bucket"
        test_key = "test-file.parquet"
        
        s3_client.create_bucket(
            Bucket=test_bucket,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
        )
        
        with patch('boto3.client') as mock_boto:
            mock_s3 = MagicMock()
            mock_s3.head_object.side_effect = ClientError(
                {"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadObject"
            )
            mock_boto.return_value = mock_s3
            
            with pytest.raises(ClientError):
                check_file_exists_in_processed_bucket(test_bucket, test_key)