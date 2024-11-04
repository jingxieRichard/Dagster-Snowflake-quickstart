from dagster import (
    Definitions, 
    EnvVar,
    ScheduleDefinition, 
    define_asset_job, 
    load_assets_from_package_module,
)
from dagster_snowflake_pandas import SnowflakePandasIOManager
from dagster_snowflake import SnowflakeResource

from . import quickstart, braze_data_processor  # noqa: TID252



daily_refresh_schedule = ScheduleDefinition(
    job=define_asset_job(name="all_assets_job"), cron_schedule="0 0 * * *"
)


# Load assets from each module
braze_assets = load_assets_from_package_module(braze_data_processor)
quickstart_assets = load_assets_from_package_module(quickstart)

# Define jobs for each asset group
braze_job = define_asset_job(name="braze_job", selection=braze_assets)
quickstart_job = define_asset_job(name="quickstart_job", selection=quickstart_assets)

# Define resources for each job 
quickstart_sf_resource = SnowflakePandasIOManager(
            # Read about using environment variables and secretes in Dagster: 
            # https://docs.dagster.io/guides/dagster/using-environment-variables-and-secrets
            account=EnvVar("SNOWFLAKE_ACCOUNT").get_value(),
            user=EnvVar("SNOWFLAKE_USER").get_value(),
            password=EnvVar("SNOWFLAKE_PASSWORD").get_value(),
            warehouse=EnvVar("SNOWFLAKE_WAREHOUSE").get_value(),
            database=EnvVar("SNOWFLAKE_DATABASE").get_value(),
            schema=EnvVar("SNOWFLAKE_SCHEMA").get_value(),
        )
braze_sf_resource = SnowflakeResource(
            account=EnvVar("SNOWFLAKE_ACCOUNT"),
            user=EnvVar("SNOWFLAKE_USER"),
            password=EnvVar("SNOWFLAKE_PASSWORD"),
            warehouse="JING_TEST_WH", 
            ROLE="JING_TEST_ROLE"
        )


defs = Definitions(
    assets=braze_assets + quickstart_assets,
    jobs=[braze_job, quickstart_job],
    resources={
        "snowflake": braze_sf_resource,
        "io_manager": quickstart_sf_resource,
    },
        
    schedules=[daily_refresh_schedule]
)