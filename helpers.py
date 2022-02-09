from pathlib import Path
from datetime import datetime
from loguru import logger


def create_todays_path():
    now = datetime.now()
    current_dir_path = Path(__file__).absolute().parent
    data_path = Path(f"{current_dir_path}/data/{now.strftime('%Y')}/{now.strftime('%m')}/{now.strftime('%d')}")
    data_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Path created: {data_path}")
    return data_path


