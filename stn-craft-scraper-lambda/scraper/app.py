import json
import os

from requests_html import HTMLSession
import pandas as pd
from datetime import datetime
from aws_lambda_powertools import Logger

logger = Logger(service="stn-craft-scraper")

def create_todays_path():
    now = datetime.now()
    date_path = f"{now.strftime('%Y')}/{now.strftime('%m')}/{now.strftime('%d')}"
    return date_path

class ExportSTNCraft:
    def __init__(self):
        self.session = HTMLSession()
        self.base_page = "https://stn-craft.com"

    def get_links(self, url, search_word):
        r = self.session.get(url=url)
        if search_word:
            return [link for link in r.html.links if search_word in link]
        else:
            return r.html.links

    def get_page(self, url):
        r = self.session.get(url)
        return r.html

    def parse_product_details(self, product_page):
        image_object_list = product_page.find('.woocommerce-product-gallery')[-1].find('img')
        images_list = [img.attrs['src'] for img in image_object_list]

        product_info = {
            'Название_позиции': product_page.find('.product_title')[-1].text,
            'Цена': product_page.find('.amount')[-1].text.split('\xa0')[0],
            'Описание': product_page.find('.woocommerce-Tabs-panel--description')[-1].text,
            'Ссылка_изображения': images_list[0]

        }
        return product_info

    def export_runes_data(self, to_csv=False):
        self.runes_pages_list = [
            f"{self.base_page}/product-category/rune-sets/",
            f"{self.base_page}/product-category/rune-sets/page/2/"
        ]
        rune_data = []
        for runes_page in self.runes_pages_list:
            logger.info(f"Scraping {runes_page}....")
            for link in self.get_links(runes_page, 'runy'):
                product_page = self.get_page(link)
                product_details = self.parse_product_details(product_page)
                rune_data.append(product_details)
            logger.info("Done.")
        runes_df = pd.DataFrame(rune_data)
        file_path = create_todays_path()
        filename = "stn_craft_runes.csv"
        logger.info(f"Saving {filename} to {file_path}")
        if to_csv:
            runes_df.to_csv(
                path_or_buf=f"{file_path}/{filename}",
                index=False
            )
        return runes_df


class Import2Prom:
    def __init__(self, token=None):
        self.token = token

    def build_prom_csv(self, input_data):
        """
        https://public-api.docs.prom.ua/#/Products/post_products_import_file
        """
        logger.info("Building prom like csv...")
        prom_schema = pd.read_csv('templates/prom_import_template.csv', sep=';')
        prom_schema = prom_schema.append(input_data, ignore_index=True)
        prom_schema['Цена'] = [el.split('\xa0')[0].replace(' ', '') for el in prom_schema['Цена'].to_list()]
        prom_schema['Единица измерения'] = 'шт.'
        prom_schema['Валюта'] = 'UAH'
        prom_schema['Количество'] = 0
        filename = "stn_craft_runes_prom.csv"
        filepath = create_todays_path()
        logger.info(f"Saving {filename} to {filepath}")
        prom_schema.to_csv(f's3://{os.environ.get("S3_BUCKET")}/stn-craft/{filepath}/{filename}', index=False)
        return


def lambda_handler(event, context):
    parsed_df = ExportSTNCraft().export_runes_data()
    Import2Prom().build_prom_csv(parsed_df)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Products sucessfully parsed and saved to s3 bucket"
        }),
    }
