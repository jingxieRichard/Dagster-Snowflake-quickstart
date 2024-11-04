from snowflake.snowpark.session import Session 


def get_sf_connection():
    connection_params = {"connection_name": "default"}
    
    return Session.builder.configs(connection_params).create()