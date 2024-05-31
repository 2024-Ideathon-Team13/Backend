from dotenv import load_dotenv
import os

load_dotenv()

sql_alchemy_database_url = os.environ.get('SQLALCHEMY_DATABASE_URL')
CREDENTIALS_ACCESS_KEY = os.environ.get('CREDENTIALS_ACCESS_KEY')
CREDENTIALS_SECRET_KEY = os.environ.get('CREDENTIALS_SECRET_KEY')
CREDENTIALS_AWS_REGION = os.environ.get('CREDENTIALS_AWS_REGION')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')