import os
import sys
import json
import httpx
from httpcore import ReadTimeout
import pandas as pd
from datetime import datetime
from time import sleep
import math
from aws_lambda_powertools import Logger

logger = Logger(service="dom-ria-scraper")


class DomScraper:
    def __init__(self):
        self.allowed_requests_per_hour = 1000
        logger.append_keys(allowed_requests_per_hour=self.allowed_requests_per_hour)
        self.ria_api_key = os.environ.get("RIA_API_KEY")
        self.s3_bucket_base_path = f's3://{os.environ.get("S3_BUCKET")}/dom-ria'

    def get_flat_ids_from_page(self, page):
        try:
            resp = httpx.get(f"https://developers.ria.com/dom/search?api_key={self.ria_api_key}&category=1&realty_type=2&operation_type=1&fullCategoryOperation=1_2_1&wo_dupl=1&page={page}&state_id=5&city_id=5&limit=20&sort=inspected_sort&period=0&csrf=2yNDQzHF-68XudDiYcVYYZBQ5b9LA6BvBxXA&ch=209_f_2,209_t_3,242_239,247_252,265_0")
            if self.quota_is_not_reached(resp):
                flat_ids_df = pd.DataFrame(resp.json())
                flat_ids_df['checked'] = False
                return flat_ids_df
            else:
                self.get_flat_ids_from_page(page)
        except ReadTimeout:
            self.get_flat_ids_from_page(page)

    def quota_is_not_reached(self, resp):
        self.allowed_requests_per_hour -= 1
        logger.debug(f"Allowed requests per hour {self.allowed_requests_per_hour}/1000")
        if resp.status_code == 200:
            return True
        elif resp.status_code == 429:
            msg = f"Quota is reached at {self.allowed_requests_per_hour} need to wait 1h"
            logger.warning(msg)
            return False
        else:
            msg = f"Received {resp.status_code} with content: {resp.content}"
            logger.exception(msg)
            sys.exit(msg)

    def get_flats_ids_df(self):
        current_page = 0
        df = self.get_flat_ids_from_page(current_page)
        found_flats = df['count'].values.tolist()[0]
        logger.append_keys(flats_found=found_flats)
        if found_flats > 100:
            total_pages = int(math.ceil(found_flats / df['items'].count()))
            logger.append_keys(total_pages=total_pages)
            for page in range(total_pages):
                logger.append_keys(page=current_page)
                if page == current_page:
                    logger.debug(f"Skipping page {page} as it is same as current page {current_page}")
                    continue
                else:
                    df = pd.concat([df, self.get_flat_ids_from_page(page)], ignore_index=True)
                    logger.info(f"Getting data from page number {page}")
                    if self.allowed_requests_per_hour < total_pages:
                        self.export_flats_ids_to_s3(df, page=current_page)
                        logger.warning("Too low allowed requests. quitting..")
                        sys.exit("Too low allowed requests. quitting..")
                    current_page = page
            logger.info("Flats ids list saving finished")
        self.export_flats_ids_to_s3(df, page=current_page)
        return df


    def get_flat_info(self, flat_id):
        try:
            resp = httpx.get(f"https://developers.ria.com/dom/info/{flat_id}?api_key={self.ria_api_key}")
            if self.quota_is_not_reached(resp):
                try:
                    resp = pd.DataFrame(resp.json())
                except ValueError as e:
                    resp = pd.DataFrame.from_dict(resp.json(), orient='index')
                return resp
            else:
                return False
        except ReadTimeout:
            sleep(5)
            self.get_flat_info(flat_id)

    def export_flats_ids_to_s3(self, flats_ids_df, page=0):
        now = datetime.now()
        filename = f"flat_ids_list_{now.hour}_page_{page}.csv"
        filepath = f"{create_storage_path()}"
        flats_ids_df.to_csv(f'{self.s3_bucket_base_path}/{filepath}/{filename}', index=False)
        logger.info(f"Data written to {filepath}:{filename}")

    def export_flats_info_to_s3(self, flats_df):
        now = datetime.now()
        filename = f"flats_data_list_{now.hour}_page.csv"
        filepath = f"{create_storage_path()}"
        flats_df.to_csv(f'{self.s3_bucket_base_path}/{filepath}/{filename}', index=False)
        logger.info(f"Data written to {filepath}:{filename}")


    def get_flats_data(self, flats_ids_df):
        number_of_flats = flats_ids_df['items'].count()
        flats_df_list = []
        for ind in flats_ids_df.index:
            df = self.get_flat_info(flats_ids_df['items'][ind])
            if not df:
                flats_df_list = pd.concat(flats_df_list, axis=0, ignore_index=True)
                self.export_flats_info_to_s3(flats_df_list)
                self.export_flats_ids_to_s3(flats_ids_df)
            flats_df_list.append(df)
            flats_ids_df.loc[flats_ids_df.index == ind, 'checked'] = True
            number_of_flats -= 1
            logger.info(f"Flats remaining {number_of_flats}/{flats_ids_df['items'].count()}")
            if self.allowed_requests_per_hour < 2:
                flats_df_list = pd.concat(flats_df_list, axis=0, ignore_index=True)
                self.export_flats_info_to_s3(flats_df_list)
                self.export_flats_ids_to_s3(flats_ids_df)
        flats_df_list = pd.concat(flats_df_list, axis=0, ignore_index=True)
        self.export_flats_info_to_s3(flats_df_list)
        self.export_flats_ids_to_s3(flats_ids_df)


def create_storage_path(granularity='minute'):
    now = datetime.now()
    if granularity == 'hour':
        filepath = f"{now.year}/{now.month}/{now.day}/{now.hour}"
    elif granularity == 'day':
        filepath = f"{now.year}/{now.month}/{now.day}"
    else:
        filepath = f"{now.year}/{now.month}/{now.day}/{now.hour}/{now.minute}"
    return filepath


if __name__ == "__main__":
    dom = DomScraper()
    flats_id_df = dom.get_flats_ids_df()
    dom.get_flats_data(flats_id_df)
    # return {
    #     "statusCode": 200,
    #     "body": json.dumps({
    #         "message": "Flats data sucessfully parsed and saved to s3 bucket"
    #     }),
    # }

