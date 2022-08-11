import os
import sys
import datetime
import csv
import json
import argparse

import httpx
import fake_useragent
import pandas as pd
from loguru import logger
from sys import stderr

FOLDER_TO_SAVE = 'parsing'

session = httpx.Client()
session.headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'user-agent': fake_useragent.UserAgent().chrome}
path = os.path.join(os.getcwd(), FOLDER_TO_SAVE)
if not os.path.exists(path):
    os.mkdir(FOLDER_TO_SAVE)

logger.remove()
logger.add(stderr, format="<white>{time:HH:mm:ss}</white>"
                          " | <level>{level: <8}</level>"
                          " | <cyan>{line}</cyan>"
                          " - <white>{message}</white>")


# def parse_arguments():
#     parser_args = argparse.ArgumentParser()
#     parser_args.add_argument('-f', dest='file_name', help='Save file name', default=datetime.datetime.now().date(),
#                              action='file_name')
#     parser_args.add_argument('-p', dest='count_page', help='How many pages to parse', type=int, action='count_page')
#     return parser_args.parse_args(sys.argv[1:])

def sort_by_time(date):
    return datetime.time.fromisoformat(date)

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
        writer = pd.ExcelWriter(
            path=os.path.join(path, f"{self.name}_{datetime.datetime.now().strftime('%d_%m_%Y')}.xlsx"),
            engine='xlsxwriter')
        write_data.to_excel(writer, index=False)
        # write_data.to_excel(writer, index=False, columns=['id', 'brand', 'name', 'old_price', 'new_price', 'sale', 'rating', 'count_of_feedbacks'])
        writer.save()

    def write_items_to_csv(self):
        with open(os.path.join(path, f"{self.name}_{datetime.datetime.now().strftime('%d_%m_%Y')}.csv"), 'w',
                  encoding='utf-16', errors='ignore') as f:
            writer = csv.DictWriter(f, fieldnames=[i for i in self.items[0].keys()], delimiter='\t',
                                    lineterminator="\r")
            writer.writeheader()
            for item in self.items:
                writer.writerow(item)

    @logger.catch
    def get_data_and_parse(self, count_page_for_parsing: int):
        self._get_params()
        data = session.get('https://search.wb.ru/exactmatch/ru/common/v4/search', params=self.params).json()
        self.name = data.get('metadata').get('name')
        counter = 1
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
                add_data = {
                    'id': id,
                    'brand': brand,
                    'name': name,
                    'old_price': old_price,
                    'new_price': new_price,
                    'sale': sale,
                    'rating': rating,
                    'count_of_feedbacks': count_of_feedbacks,
                    'url': f'https://www.wildberries.ru/catalog/{id}/detail.aspx'
                }
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
                try:
                    price_history = session.get(f'https://wbx-content-v2.wbstatic.net/price-history/{id}.json').json()
                except json.decoder.JSONDecodeError:
                    price_history = []
                prices = {}
                for price in price_history[::-1]:
                    time = datetime.datetime.fromtimestamp(price.get('dt'))
                    if time.month == datetime.datetime.now().month-1:
                        price = price.get('price').get('RUB', 0) // 100
                        # prices.append({'time': time, time: price})
                        # prices.append({time.strftime('%d.%m.%Y'): price})
                        prices[time.strftime('%d.%m.%Y')] = price
                        # add_data[time.strftime('%d.%m.%Y')] = price
                prices = dict(sorted(prices.items(), key=lambda x: x[0]))
                add_data.update(**prices)
                # print(dict(prices))
                # prices.sort(key=lambda dictionary: dictionary['time'])
                # for price in prices:
                #     time = price.get('time')
                #     add_data[time] = price.get(time)
                self.items.append(add_data)
            logger.success(f'Страница {counter} успешно собрана')
            if counter >= count_page_for_parsing:
                break
            counter += 1
            self.params['page'] = str(int(self.params.get('page')) + 1)
            data = session.get('https://search.wb.ru/exactmatch/ru/common/v4/search', params=self.params).json()
        # self.write_items_to_csv()


if __name__ == '__main__':
    url = input('Введите ссылку для парсинга: ')
    a = Wildberries_Parser(url)
    a.get_data_and_parse(10)
    a.write_items_to_excel()

