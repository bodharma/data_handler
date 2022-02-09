import pandas as pd
from api.notion import Notion
from helpers import create_todays_path


def export_data_from_notion():
    notion = Notion(token="")
    notion_data = notion.export_data_from_table(_id="adf5c3e8fcd64ccab2c0f749a1e4784d")
    normalized_data_df = pd.DataFrame(notion.convert_notion_to_dict(input_data=notion_data))
    normalized_data_df['Currency'] = 'UAH'
    normalized_data_df['measure'] = 'шт.'
    path = create_todays_path()
    filepath = f"{path}/exported_notion_db_data.csv"
    normalized_data_df.to_csv(path_or_buf=filepath)
    return normalized_data_df


def convert_data_to_prom_format():
    pass


def send_data_to_prom():
    pass


if __name__ == "__main__":
    export_data_from_notion()
