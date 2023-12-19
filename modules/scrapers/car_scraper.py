import os
import sys
import time
import pathlib
import httpx
import pandas as pd
import requests
from bs4 import BeautifulSoup

from modules.scrapers.get_advertisement import AdvertisementFetcher
import logging
from loguru import logger
from tqdm import tqdm
from resources.headers import PAGE_HEADER


class CarScraper:
    """
        Scraps cars from otomoto.pl
        Args:
            model_file_path: path to file with models
            data_directory: path to directory where data will be saved
    """

    def __init__(self, model_file_path, data_directory):
        self.model_file_path = os.path.join(os.getcwd(), model_file_path)
        self.data_directory = os.path.join(os.getcwd(), data_directory,'data')
        self.log_directory = os.path.join(os.getcwd(), data_directory, 'logs')
        self.models = self._read_models()
        self.ad_fetcher = AdvertisementFetcher()
        self.header = PAGE_HEADER

        pathlib.Path(self.data_directory).mkdir(parents=True,exist_ok=True)

        log_level = "DEBUG"
        log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS zz}</green> | <level>{level: <8}</level>  <b>{message}</b>"
        logger.add(os.path.join(self.log_directory,'log.txt'), level=log_level, format=log_format, colorize=False, backtrace=True, diagnose=True)


    def _read_models(self):
        with open(self.model_file_path, 'r', encoding='utf-8') as file:
            models = file.readlines()
        return models

    def get_cars_in_page(self, path, i):
        """
            Gets cars in page
            Args:
                path: path to page
                i: page number
            return:
                list of links
        """
        logger.info(f'Scrapping page: {i}')
        res = requests.get(f'{path}?page={i}', headers=self.header)
        soup = BeautifulSoup(res.content,'html.parser')
        car_links_section = soup.find('div', {'data-testid': 'search-results'})
        links = []
        for x in car_links_section.find_all('div'):
            try:
                links.append(
                    x.find(
                        'article',
                        attrs={
                            'data-media-size': True
                        }
                    ).find('a', href=True)['href']
                )
            except Exception:
                pass
        logger.info(f'Found {len(links)} links')
        return links

    def scrap_model(self, model):
        """
            Scraps model
            Args:
                 model: model to scrap
        """
        model = model.strip()
        logger.info(f'Start scrapping model: {model}')
        self.ad_fetcher.setup_fetcher()
        path = f'https://www.otomoto.pl/osobowe/{model}'
        try:
            res = requests.get(path)
            res = httpx.get(path, headers=self.header)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, features='lxml')
            last_page_num = int(soup.find_all(
                'li', attrs={'data-testid': 'pagination-list-item'})[-1].text)
        except Exception:
            last_page_num = 1
        last_page_num = min(last_page_num, 500)

        logger.info(f'Model has: {last_page_num} subpages')

        pages = range(1, last_page_num + 1)
        for page in tqdm(pages):
            links = self.get_cars_in_page(path, page)
            self.ad_fetcher.fetch_ads(links)
        self.ad_fetcher.save_ads(model)

        logger.info(f'End Scrapping model: {model}')

    def scrap_all_models(self):
        logger.info('Starting scrapping cars...')
        for model in self.models:
            self.scrap_model(model)
        logger.info('End scrapping cars')

    def combine_data(self):
        logger.info('Combining data...')

        xlsx_filenames = [os.path.join(self.data_directory,file) for file in os.listdir(self.data_directory)]
        combined_data = []
        print(xlsx_filenames)
        for filename in xlsx_filenames:
            try:
                combined_data.append(pd.read_excel(
                    filename, index_col='Unnamed: 0'))
            except Exception:
                pass
        df_all = pd.concat(combined_data, ignore_index=True)
        df_all.to_csv('car.csv', index=False)
        logger.info('Combined data saved to car.csv')
