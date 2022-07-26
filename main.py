import os
import sys
import datetime
import csv
import argparse


import httpx
import fake_useragent
import pandas as pd

FOLDER_TO_SAVE = 'parsing'

session = httpx.Client()
session.headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'user-agent': fake_useragent.UserAgent().chrome}
path = os.path.join(os.getcwd(), FOLDER_TO_SAVE)
if not os.path.exists(path):
    os.mkdir(FOLDER_TO_SAVE)

# def parse_arguments():
#     parser_args = argparse.ArgumentParser()
#     parser_args.add_argument('-f', dest='file_name', help='Save file name', default=datetime.datetime.now().date(),
#                              action='file_name')
#     parser_args.add_argument('-p', dest='count_page', help='How many pages to parse', type=int, action='count_page')
#     return parser_args.parse_args(sys.argv[1:])


class Wildberries_Parser:
    items = []

    def __init__(self, url):
        self.url = url
        self.name = 'wildberries'

    def _get_params(self):
        url = self.url.split('?')[-1].replace('search', 'query').split('&')
        data_params = session.post('https://www.wildberries.ru/webapi/user/get-xinfo-v2',
                                   headers={'accept': '*/*', 'x-requested-with': 'XMLHttpRequest'}).json().get(
            'xinfo').split('&')
        self.params = {
            'resultset': 'catalog',
            'page': '1'
        }
        for param in data_params:
            param = param.split('=')
            self.params[param[0]] = param[-1]
        for param in url:
            param = param.split('=')
            self.params[param[0]] = param[-1]
        return self.params

    def write_items_to_excel(self):
        write_data = pd.DataFrame(self.items)
        writer = pd.ExcelWriter(path=os.path.join(path, f"{self.name}_{datetime.datetime.now().strftime('%d_%m_%Y')}.xlsx"), engine='xlsxwriter')
        write_data.to_excel(writer, index=False)
        # write_data.to_excel(writer, index=False, columns=['id', 'brand', 'name', 'old_price', 'new_price', 'sale', 'rating', 'count_of_feedbacks'])
        writer.save()

    def write_items_to_csv(self):
        with open(os.path.join(path, f"{self.name}_{datetime.datetime.now().strftime('%d_%m_%Y')}.csv"), 'w', encoding='utf-16', errors='ignore') as f:
            writer = csv.DictWriter(f, fieldnames=[i for i in self.items[0].keys()], delimiter='\t', lineterminator="\r")
            writer.writeheader()
            for item in self.items:
                writer.writerow(item)

    def get_data_and_parse(self):
        self._get_params()
        data = session.get('https://search.wb.ru/exactmatch/ru/common/v4/search', params=self.params).json()
        self.name = data.get('metadata').get('name')
        while data.get('data').get('products'):
            for product in data.get('data').get('products'):
                brand = product.get('brand')
                count_of_feedbacks = product.get('feedbacks')
                name = product.get('name')
                rating = product.get('rating')
                sale = product.get('sale')
                old_price = int(product.get('priceU')) // 100
                new_price = int(product.get('salePriceU')) // 100
                id = product.get('id')
                # self.items[id] = {
                #     'id': id,
                #     'brand': brand,
                #     'name': name,
                #     'old_price': old_price,
                #     'new_price': new_price,
                #     'sale': sale,
                #     'rating': rating,
                #     'count_of_feedbacks': count_of_feedbacks
                # }
                self.items.append({
                    'id': id,
                    'brand': brand,
                    'name': name,
                    'old_price': old_price,
                    'new_price': new_price,
                    'sale': sale,
                    'rating': rating,
                    'count_of_feedbacks': count_of_feedbacks,
                    'url': f'https://www.wildberries.ru/catalog/{id}/detail.aspx'
                })
            self.params['page'] = str(int(self.params.get('page')) + 1)
            data = session.get('https://search.wb.ru/exactmatch/ru/common/v4/search', params=self.params).json()
        # self.write_items_to_csv()
        self.write_items_to_excel()
if __name__ == '__main__':
    url = input('Введите ссылку для парсинга: ')
    Wildberries_Parser(url).get_data_and_parse()