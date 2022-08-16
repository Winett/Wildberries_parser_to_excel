import asyncio
import os
import sys
import datetime
import csv
import json
import argparse
import time

from httpx import AsyncClient
import httpx
import fake_useragent
import pandas as pd
from loguru import logger
from sys import stderr

FOLDER_TO_SAVE = 'parsing'

session = AsyncClient()
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


def sort_by_time(date):
    return datetime.time.fromisoformat(date)


class Async_Wildberries_Parser:
    items = []

    def __init__(self, url):
        self._params = {}
        self._url = url
        self._name = 'wildberries'

    def write_items_to_excel(self):
        write_data = pd.DataFrame(self.items)
        writer = pd.ExcelWriter(
            path=os.path.join(path, f"{self._name}_{datetime.datetime.now().strftime('%d_%m_%Y')}.xlsx"),
            engine='xlsxwriter')
        write_data.to_excel(writer, index=False)
        # write_data.to_excel(writer, index=False, columns=['id', 'brand', 'name', 'old_price', 'new_price', 'sale', 'rating', 'count_of_feedbacks'])
        writer.save()

    async def _get_params(self):
        url = self._url.split('?')[-1].replace('search', 'query').split('&')
        data_params = await session.post('https://www.wildberries.ru/webapi/user/get-xinfo-v2',
                                         headers={'accept': '*/*', 'x-requested-with': 'XMLHttpRequest'})
        data_params = data_params.json().get('xinfo').split('&')
        self._params = {
            'resultset': 'catalog',
            'page': '1'
        }
        for param in data_params:
            param = param.split('=')
            self._params[param[0]] = param[-1]
        for param in url:
            param = param.split('=')
            self._params[param[0]] = param[-1]
        return self._params

    @property
    def params(self):
        return self._params

    @params.setter
    def params(self, value):
        self._params = value

    @logger.catch
    async def get_data_and_parse(self, params: dict):
        data = await session.get('https://search.wb.ru/exactmatch/ru/common/v4/search', params=params)
        data = data.json()
        if data.get('data').get('products'):
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
                try:
                    price_history = await session.get(f'https://wbx-content-v2.wbstatic.net/price-history/{id}.json')
                    price_history = price_history.json()
                except json.decoder.JSONDecodeError:
                    price_history = []
                prices = {}
                for price in price_history[::-1]:
                    time = datetime.datetime.fromtimestamp(price.get('dt'))
                    if time.month == datetime.datetime.now().month:
                        price = price.get('price').get('RUB', 0) // 100
                        # prices.append({'time': time, time: price})
                        # prices.append({time.strftime('%d.%m.%Y'): price})
                        prices[time.strftime('%d.%m.%Y')] = price
                        # add_data[time.strftime('%d.%m.%Y')] = price
                prices = dict(sorted(prices.items(), key=lambda x: x[0]))
                add_data.update(**prices)
                self.items.append(add_data)
            page = params['page']
            logger.success(f'Страница {page} успешно собрана')

    @logger.catch
    async def creating_tasks(self, count_page_for_parsing: int):
        await self._get_params()
        data = await session.get('https://search.wb.ru/exactmatch/ru/common/v4/search', params=self._params)
        data = data.json()
        self._name = data.get('metadata').get('name')
        tasks = []
        for page in range(1, count_page_for_parsing+1):
            params = self._params.copy()
            params['page'] = page
            tasks.append(asyncio.create_task(self.get_data_and_parse(params=params)))
        await asyncio.wait(tasks)
        self.write_items_to_excel()

async def main():
    resp = await session.post('https://www.wildberries.ru/webapi/user/get-xinfo-v2',
                                         headers={'accept': '*/*', 'x-requested-with': 'XMLHttpRequest'})
    print(resp.json())

if __name__ == '__main__':
    # url = input('Введите ссылку для парсинга: ')
    url = 'https://www.wildberries.ru/catalog/0/search.aspx?sort=popular&search=телефоны'
    a = Async_Wildberries_Parser(url)
    start = time.time()
    asyncio.run(a.creating_tasks(30), debug=True)
    print(f'Сделал всё за {round(time.time() - start, 1)} секунд')
    asyncio.to_thread()