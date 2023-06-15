import os
import sys
sys.path.append( os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))) )

from config import config
environment = 'local'
config['LOG_PRINT'] = 0
config['LOG_NAME'] = 'chat-retrieval-plugin'

os.environ["REDIS_PORT"] = "7379"

import utils
