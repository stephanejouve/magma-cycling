poetry run python -c "
import os
from dotenv import load_dotenv
load_dotenv()

print('1. ENV:', os.getenv('TRAINING_DATA_REPO'))

from cyclisme_training_logs.config import get_data_config
config = get_data_config()

print('2. CONFIG data_repo_path:', config.data_repo_path)
print('3. CONFIG workouts_history:', config.workouts_history_path)
print('4. Exists?', config.data_repo_path.exists())
"
