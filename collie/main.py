import json

from requests_html import HTMLSession
import httpx

session = HTMLSession()
base_page = "http://www.collie.com.ua/"


def get_links(end_of_url):
    r = session.get(f'{base_page}{end_of_url}')
    return r.html.links


def get_page_data(end_of_url):
    r = session.get(f'{base_page}{end_of_url}')
    return r.html


def filter_links(links_list, end_of_url):
    return [link for link in links_list if end_of_url.split('?')[-1] in link]


def normalize_string(string):
    return string.split('=')[-1]


def build_dict_data_from_links(parsed_links_list, dogs_dict, dog_per_category_dict):
    category = None

    for link in parsed_links_list:
        try:
            parent, category, name = link.split('&')
        except ValueError:
            continue
        category = normalize_string(category)
        name = normalize_string(name)
        if category not in dog_per_category_dict.keys():
            dog_per_category_dict[category] = {}
        dog_per_category_dict[category][name] = {"link": link}

    if category:
        dogs_dict[category] = dog_per_category_dict


def get_dog_details(dog_page):
    dog_page_tables_list = dog_page.find('table')
    breed_table = []
    breed_dict = {
        'child': {
        }
    }
    dog_images_links_list = []
    dog_description = []
    column_1, column_2, column_3, column_4 = '', '', '', ''
    for table in dog_page_tables_list:
        if 'id' in table.attrs:
            if table.attrs['id'] == 'main_content':
                dog_images_links_list = [f"{img.attrs['src']}" for img in table.find('img')]
                for el in table.find('p'):
                    if 'style' in el.attrs.keys():
                        if el.attrs['style'] == 'text-align: center;':
                            if el.text:
                                dog_description.append(el.text)
        elif 'style' in table.attrs:
            if table.attrs['style'] == "font-size:16px;":
                table_rows = table.find('tr')
                for row in table_rows:
                    columns = row.find('td')
                    columns_len = len(columns)
                    if columns_len == 4:
                        column_1, column_2, column_3, column_4 = columns
                    elif columns_len == 3:
                        column_2, column_3, column_4 = columns
                    elif columns_len == 2:
                        column_3, column_4 = columns
                    elif columns_len == 1:
                        column_4 = columns[-1]
                    columns_list = tuple(column.text if type(column) != str else column for column in
                                         (column_1, column_2, column_3, column_4))
                    breed_table.append(columns_list)
    for entry in breed_table:
        parent, grand, great_grand, great_great_grand = entry
        if parent not in breed_dict['child'].keys():
            breed_dict['child'][parent] = {}
        if grand not in breed_dict['child'][parent].keys():
            breed_dict['child'][parent][grand] = {}
        if great_grand not in breed_dict['child'][parent][grand].keys():
            breed_dict['child'][parent][grand][great_grand] = {}
        if great_great_grand not in breed_dict['child'][parent][grand][
            great_grand].keys() and 'Nataly' not in great_great_grand:
            breed_dict['child'][parent][grand][great_grand][great_great_grand] = {}

    dog_details_dict = {
        'images_list': dog_images_links_list,
        'breed_tree': breed_dict,
        'breed_table': breed_table,
        'dog_description': dog_description
    }
    return dog_details_dict


def parse_dog_page():
    dog_per_category_dict = {}
    main = "index.php"
    bitches = 'our_collies.php?cat=Bitches'
    kids = 'our_collies.php?cat=Hopes'
    males = 'our_collies.php?cat=Males'
    dog_pages = [bitches, males]

    for dog_page in dog_pages:
        dogs_dict = {}
        links_list = get_links(dog_page)
        parsed_links_list = filter_links(links_list, end_of_url=dog_page)
        build_dict_data_from_links(
            parsed_links_list=parsed_links_list,
            dogs_dict=dogs_dict,
            dog_per_category_dict=dog_per_category_dict
        )

        dog_per_category_dict_copied = dog_per_category_dict.copy()
        for category, dogs_dict in dog_per_category_dict_copied.items():
            for dog_name, attrs in dogs_dict.items():
                dog_details_dict = get_dog_details(dog_page=get_page_data(attrs["link"]))
                dog_per_category_dict[category][dog_name]['details'] = dog_details_dict
    return dog_per_category_dict


def get_db_data(db_id, notion_token):
    resp = httpx.patch(
        url=f'https://api.notion.com/v1/databases/{db_id}',
        headers={
            'Authorization': f'Bearer {notion_token}',
            "Notion-Version": "2021-08-16"
        }
    )
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Got {resp.status_code} error: {resp.json()}")


def import_data_to_notion_db(db_id, notion_token, dog_data):
    request_body = {
        'parent': {'database_id': db_id},
        'properties': {
            'Name': {'title': [{'text': {'content': dog_data['Name']}}]},
            'Photo': {'files': dog_data['Photo']},
            'Date of birth': {"date": {"start": "2021-05-11T11:00:00.000-04:00"}},
            'Genetic tests': {'multi_select': [
                {'name': 'Test'},
            ]},
            'Breeder': {'multi_select': [
                {'name': 'Test'}
            ]},
            'Titles': {'multi_select': [
                {'name': 'Test'}
            ]},
            'Gender': {'select': {
                'name': dog_data['Gender']
            }},
            'Temp': {'rich_text': [
                {
                    "text": {'content': dog_data['Temp']}}
            ]}
        },
    }
    resp = httpx.post(
        url=f'https://api.notion.com/v1/pages',
        headers={
            'Authorization': f'Bearer {notion_token}',
            "Notion-Version": "2021-08-16"
        },
        json=request_body
    )
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Got {resp.status_code} error: {resp.json()}")


def draw(parent_name, child_name):
    edge = pydot.Edge(parent_name, child_name)
    graph.add_edge(edge)

def visit(node, parent=None):
    for k,v in node.items():
        if isinstance(v, dict):
            # We start with the root node whose parent is None
            # we don't want to graph the None node
            if parent:
                draw(parent, k)
            visit(v, k)
        else:
            draw(parent, k)
            # drawing the label using a distinct name
            draw(k, k+'_'+v)




if __name__ == "__main__":
    notion_token = ""
    db_id = ""
    notion_db_link = f"https://bodh.notion.site/{db_id}?v=a6e79152b9884427835181c8b7c7f263"


    with open('dogs_data.json', 'r') as dog_file:
        dog_data_dict = json.loads(dog_file.read())

    for gender, dogs_list in dog_data_dict.items():
        for dog_name, dog_data in dogs_list.items():

            dog_images_list = []
            for counter, image in enumerate(dog_data['details']['images_list']):
                img_url = f"{base_page}{image[1:]}" if image.startswith('/') else f"{base_page}{image}"
                image_template = {
                "external": {
                    "url": img_url,
                },
                "name": f"{dog_name} {counter}",

                }
                dog_images_list.append(image_template)
            import pydot
            graph = pydot.Dot(graph_type='graph')
            dog_data['details']['breed_tree'][dog_name] = dog_data['details']['breed_tree'].pop('child')
            visit(dog_data['details']['breed_tree'])
            graph.write_png(f'{dog_name}_graph.png')

            dog_description = ' | '.join(dog_data['details']['dog_description'])
            dog_request_body = {
                'Name': dog_name,
                'Photo': dog_images_list,
                'Gender': gender,
                'Temp': dog_description,
            }
            import_data_to_notion_db(db_id, notion_token, dog_request_body)
