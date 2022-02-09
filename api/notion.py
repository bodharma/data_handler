import httpx
from loguru import logger


class Notion:
    def __init__(self, token):
        self._token = token
        self.notion_api_version = "2021-08-16"

    @staticmethod
    def notion_db_data_types_import_schema(data_type, value):
        data_types_dict = {
            "file": {'files': value},
            "text": {'rich_text': [{"text": {'content': value}}]},
            "multiselect": {'multi_select': [{'name': value}, ]},
            "date": {"date": {"start": value}},
            "title": {'title': [{'text': {'content': value}}]},
            "select": {'select': {'name': value}}
        }
        return data_types_dict[data_type]

    def build_table_request(self, db_id, **kwargs):
        """

        :param db_id: id of the notion table
        :param kwargs: is expected in following format: {'Name': {'data_type': 'text', 'value': 'banana'}}
        :return: complete request body
        """
        request_body = {
            'parent': {'database_id': db_id},
            'properties': {},
        }
        properties = request_body['properties']

        for column_name, column_info in kwargs.items():
            properties[column_name] = Notion.notion_db_data_types_import_schema(
                data_type=column_info['data_type'],
                value=column_info['value']
            )

        return request_body

    def import_data_to_table(self, data: dict):
        resp = httpx.post(
            url=f'https://api.notion.com/v1/pages',
            headers={
                'Authorization': f'Bearer {self._token}',
                "Notion-Version": self.notion_api_version
            },
            json=data
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"Got {resp.status_code} error: {resp.json()}")

    def get_table_column_names_list(self, _id):
        resp = httpx.get(
            url=f'https://api.notion.com/v1/databases/{_id}',
            headers={
                'Authorization': f'Bearer {self._token}',
                "Notion-Version": self.notion_api_version
            }
        )
        if resp.status_code == 200:
            return list(resp.json()['properties'].keys())
        else:
            print(f"Got {resp.status_code} error: {resp.json()}")

    def export_data_from_table(self, _id):
        resp = httpx.post(
            url=f'https://api.notion.com/v1/databases/{_id}/query',
            headers={
                'Authorization': f'Bearer {self._token}',
                "Notion-Version": self.notion_api_version
            }
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"Got {resp.status_code} error: {resp.json()}")

    def convert_notion_to_dict(self, input_data):
        data_items_list = input_data['results']
        output_data_list = []
        for item in data_items_list:
            output_data_dict = {}
            props = item['properties']
            for column_name, column_value in props.items():
                column_type = column_value['type']
                if column_type == 'select':
                    if column_value[column_type]:
                        value = column_value[column_type]['name']
                    else:
                        value = ''
                elif column_type in ['rich_text', 'title']:
                    rich_text_list = column_value[column_type]
                    if rich_text_list:
                        value = rich_text_list[-1]['plain_text']
                    else:
                        value = ''
                elif column_type == 'files':
                    if column_value[column_type]:
                        files_list = [f['file']['url'] for f in column_value[column_type]]
                        value = files_list[0]
                    else:
                        value = ''
                elif column_type == 'url':
                    value = column_value[column_type]
                else:
                    logger.warning(f"Unrecognized type: {column_type} for column: {column_name}")
                    value = ""
                output_data_dict[column_name] = value
            output_data_list.append(output_data_dict)
        return output_data_list
