import os, sys
import os.path as path
# Set the home directory of this package
HEARTHBOT_HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(HEARTHBOT_HOME)

# Set resource paths
HEARTH_DB = os.path.join(HEARTHBOT_HOME, 'db')
TINGLE_LOGS = os.path.join(HEARTHBOT_HOME, 'tingle_logs')
