from quickstart_snowflake.braze_user_data.braze_user_data import BrazeDataProcessor

from dagster_snowflake import SnowflakeResource
from dagster import MaterializeResult, asset 


# Create a database and schema 
@asset
def create_database(snowflake: SnowflakeResource) -> None: 
    queries = [
        "USE ROLE JING_TEST_ROLE;",
        "CREATE OR REPLACE DATABASE DAGSTER_TEST_DB;",
        "USE DATABASE DAGSTER_TEST_DB;",
        "CREATE OR REPLACE SCHEMA RAW_DATA;",
        "CREATE OR REPLACE SCHEMA PROCESSED_DATA;"
    ]


    with snowflake.get_connection() as conn:
        with conn.cursor() as cursor:
            for query in queries: 
                cursor.execute(query)


# A data pipeline to aggregate Braze demo user events 
@asset(deps=[create_database])
def aggregate_braze_user_events(snowflake: SnowflakeResource) -> None:
    bz_data_processor = BrazeDataProcessor()
    bz_data_processor.run()
    print("aggregattion of Braze user events has been done successfully!")


# Collect some statistics of the aggregated_user_events 
@asset(deps=[aggregate_braze_user_events])
def sf_table_statistics(snowflake: SnowflakeResource) -> MaterializeResult:
    
    query = """
        SELECT 
            COUNT (*) AS row_count, 
            COUNT(DISTINCT USER_ID) AS unique_user_count,
            MAX(NUMBER_CLICKS) AS max_clicks,
            MIN(NUMBER_CLICKS) AS min_clicks
        FROM DAGSTER_TEST_DB.PROCESSED_DATA.AGG_USER_EVENTS
        
    """   
    with snowflake.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()

        row_count, unique_user_count, max_clicks, min_clicks = result 

    return MaterializeResult(
        metadata={
            "row_count": row_count,
            "unique_user_count": unique_user_count,
            "user_max_clicks": max_clicks,
            "user_min_clicks": min_clicks}
    )
    