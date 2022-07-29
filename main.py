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

	@@ -19,6 +21,13 @@
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
	@@ -53,22 +62,28 @@ def _get_params(self):

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
	@@ -79,6 +94,17 @@ def get_data_and_parse(self):
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
	@@ -89,21 +115,33 @@ def get_data_and_parse(self):
                #     'rating': rating,
                #     'count_of_feedbacks': count_of_feedbacks
                # }
                try:
                    price_history = session.get(f'https://wbx-content-v2.wbstatic.net/price-history/{id}.json').json()
                except json.decoder.JSONDecodeError:
                    price_history = []
                prices = []
                for price in price_history[::-1]:
                    time = datetime.datetime.fromtimestamp(price.get('dt'))
                    if time.month == datetime.datetime.now().month:
                        price = price.get('price').get('RUB', 0) // 100
                        # prices.append({'time': time, time: price})
                        add_data[time.strftime('%d.%m.%Y')] = price
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
