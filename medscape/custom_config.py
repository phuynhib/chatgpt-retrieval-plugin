import os
import sys
sys.path.append( "/var/www/html/medscape/medscape-content-feed/linear_model" )

from config import config
environment = 'local'
config['LOG_PRINT'] = 0
config['LOG_NAME'] = 'chat-retrieval-plugin'

os.environ["REDIS_PORT"] = "7379"

import utils