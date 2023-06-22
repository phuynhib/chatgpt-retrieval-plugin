from dotenv import load_dotenv
import os
from os import getenv as env
dotenv_path = os.path.dirname(os.path.realpath(__file__)) + '/.env'
load_dotenv(dotenv_path)

config = {
  "REC_ENGINE2_DB": {
    "URL": env('REC_ENGINE2_DB_URL'),
  },  
}