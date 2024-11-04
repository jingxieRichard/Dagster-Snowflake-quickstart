from dataclasses import dataclass

from quickstart_snowflake.utils.snowflake_helper import get_sf_connection

from snowflake.snowpark import DataFrame 
import snowflake.snowpark.functions as F 


BZ_USER_SEND_TABLE = "BRAZE_USER_EVENT_DEMO_DATASET.PUBLIC.USERS_MESSAGES_CONTENTCARD_SEND_VIEW"
BZ_USER_IMPRESSION_TABLE = "BRAZE_USER_EVENT_DEMO_DATASET.PUBLIC.USERS_MESSAGES_CONTENTCARD_IMPRESSION_VIEW"
BZ_USER_CLICK_TABLE = "BRAZE_USER_EVENT_DEMO_DATASET.PUBLIC.USERS_MESSAGES_CONTENTCARD_CLICK_VIEW"
BZ_USER_PURCHASE_TABLE = "BRAZE_USER_EVENT_DEMO_DATASET.PUBLIC.USERS_BEHAVIORS_PURCHASE_VIEW"
BZ_USER_BEHAVIOR_TABLE = "BRAZE_USER_EVENT_DEMO_DATASET.PUBLIC.USERS_BEHAVIORS_CUSTOMEVENT_VIEW"
DATABASE_NAME = "DAGSTER_TEST_DB"
SCHEMA_NAME_SRC = "RAW_DATA"
SCHEMA_NAME_DST = "PROCESSED_DATA"

@dataclass
class BrazeDataSet:
    raw_user_sends: DataFrame
    raw_user_impressions: DataFrame
    raw_user_clicks: DataFrame
    raw_user_purchases: DataFrame
    raw_user_behaviors: DataFrame
    agg_user_events: DataFrame



class BrazeDataProcessor:
    def __init__(self) -> None:
        self.session = get_sf_connection()
        self.data = BrazeDataSet(
            raw_user_sends=None,
            raw_user_impressions=None,
            raw_user_clicks=None,
            raw_user_purchases=None,
            raw_user_behaviors=None,
            agg_user_events=None
        )
        self.session.sql("USE ROLE JING_TEST_ROLE").collect()
    
    def run(self) -> None:
        self.load_raw_bz_events()
        self.load_to_sf_table()
        self.transform()

    def load_raw_bz_events(self):
        """Load the raw Braze user events from Braze Demo Database"""

        COLUMNS = ["USER_ID", "TIME", "CONTENT_CARD_ID", "CAMPAIGN_ID"]
        self.data.raw_user_sends = self.session.table(BZ_USER_SEND_TABLE).select(*COLUMNS)
        self.data.raw_user_impressions = self.session.table(BZ_USER_IMPRESSION_TABLE).select(*COLUMNS)
        self.data.raw_user_clicks = self.session.table(BZ_USER_CLICK_TABLE).select(*COLUMNS)

        # Purchase columns
        PURCHASE_COLUMNS = ["USER_ID", "TIME", "PRODUCT_ID", "PROPERTIES"]
        self.data.raw_user_purchases = self.session.table(BZ_USER_PURCHASE_TABLE).select(*PURCHASE_COLUMNS)

        # Load a new raw event table 
        BEHAVIOR_COLUMNS = ["USER_ID", "TIME", "PROPERTIES", "AD_ID"]
        self.data.raw_user_behaviors = self.session.table(BZ_USER_BEHAVIOR_TABLE).select(*BEHAVIOR_COLUMNS)

    def load_to_sf_table(self):
        """Write the loaded raw events into SF table"""
        
        self.data.raw_user_sends.write.mode("overwrite").save_as_table(f"{DATABASE_NAME}.{SCHEMA_NAME_SRC}.USER_SENDS")
        self.data.raw_user_impressions.write.mode("overwrite").save_as_table(f"{DATABASE_NAME}.{SCHEMA_NAME_SRC}.USER_IMPRESSIONS")
        self.data.raw_user_clicks.write.mode("overwrite").save_as_table(f"{DATABASE_NAME}.{SCHEMA_NAME_SRC}.USER_CLICKS")
        self.data.raw_user_purchases.write.mode("overwrite").save_as_table(f"{DATABASE_NAME}.{SCHEMA_NAME_SRC}.USER_PURCHASES")
        self.data.raw_user_behaviors.write.mode("overwrite").save_as_table(f"{DATABASE_NAME}.{SCHEMA_NAME_SRC}.USER_BEHAVIORS")

    def transform(self):
        """ Aggregate user events """
        user_sends = self.session.table(f"{DATABASE_NAME}.{SCHEMA_NAME_SRC}.USER_SENDS")
        user_impressions = self.session.table(f"{DATABASE_NAME}.{SCHEMA_NAME_SRC}.USER_IMPRESSIONS")
        user_clicks = self.session.table(f"{DATABASE_NAME}.{SCHEMA_NAME_SRC}.USER_CLICKS")
        user_purchases = self.session.table(f"{DATABASE_NAME}.{SCHEMA_NAME_SRC}.USER_PURCHASES")

        agg_user_sends = (user_sends
                          .group_by("USER_ID").agg(F.count("*").alias("Number_sends")))
        agg_user_impressions = (user_impressions
                                .group_by("USER_ID").agg(F.count("*").alias("Number_impressions")))
        agg_user_clicks = (user_clicks
                           .group_by("USER_ID").agg(F.count("*").alias("Number_clicks")))
        agg_user_purchases = (user_purchases
                              .group_by("USER_ID").agg(F.count("*").alias("Number_purchases")))
        
        agg_user_events = (agg_user_sends
                  .join(agg_user_impressions, "USER_ID", "outer")
                  .join(agg_user_clicks, "USER_ID", "outer")
                  .join(agg_user_purchases, "USER_ID", "outer"))
        
        agg_user_events.write.mode("overwrite").save_as_table(f"{DATABASE_NAME}.{SCHEMA_NAME_DST}.agg_user_events")