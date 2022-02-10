import pandas as pd
from helpers import create_todays_path

class Prom:
    def __init__(self, token):
        self.token = token

    def convert_notion2prom(self, notion_entry):
        product_info = {
            'Название_позиции': notion_entry['name'],
            'Цена': notion_entry.find('.amount')[-1].text.split('\xa0')[0],
            'Описание': notion_entry.find('.woocommerce-Tabs-panel--description')[-1].text,
            'Ссылка_изображения': notion_entry[0]

        }

    def build_prom_schema(self):
        prom_schema = pd.read_csv('../stn-craft-scraper-lambda/scraper/templates/prom_import_template.csv', sep=';')

    def build_prom_csv(self, input_data):
        prom_schema = pd.read_csv('../stn-craft-scraper-lambda/scraper/templates/prom_import_template.csv', sep=';')
        prom_schema = prom_schema.append(input_data, ignore_index=True)
        prom_schema['Цена'] = [el.split('\xa0')[0] for el in prom_schema['Цена'].to_list()]
        prom_schema['Единица измерения'] = 'шт.'
        prom_schema['Валюта'] = 'UAH'
        prom_schema.to_csv(f'{create_todays_path()}/prom.csv', index=False)
        return
