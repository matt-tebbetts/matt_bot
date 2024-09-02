import os

async def get_db_config():

    # Retrieve environment variables
    SQLUSER = os.getenv('SQLUSER')
    SQLPASS = os.getenv('SQLPASS')
    SQLHOST = os.getenv('SQLHOST')
    SQLPORT = int(os.getenv('SQLPORT'))
    SQLDATA = os.getenv('SQLDATA')

    # Check if all environment variables were found
    for var in [SQLUSER, SQLPASS, SQLHOST, SQLPORT, SQLDATA]:
        if var is None:
            raise ValueError(f"Environment variable '{var}' not found.")

    db_config = {
        'host': SQLHOST,
        'port': SQLPORT,
        'user': SQLUSER,
        'password': SQLPASS,
        'db': SQLDATA
    }

    return db_config