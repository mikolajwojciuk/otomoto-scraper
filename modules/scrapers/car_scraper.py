import os
import pathlib
import pandas as pd
import requests
import json
from bs4 import BeautifulSoup
from modules.scrapers.adv_scraper import AdvertisementFetcher
from pathlib import Path
from loguru import logger
from tqdm import tqdm
from resources.headers import PAGE_HEADER


class CarScraper:
    """
    Scraps cars from otomoto.pl
    Args:
        data_directory: path to directory where data will be saved
    """

    def __init__(self, data_directory):
        self.data_directory = os.path.join(os.getcwd(), data_directory, "data")
        self.log_directory = os.path.join(os.getcwd(), data_directory, "logs")

        log_level = "DEBUG"
        log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS zz}</green> | <level>{level: <8}</level>  <b>{message}</b>"
        logger.add(
            os.path.join(self.log_directory, "log.txt"),
            level=log_level,
            format=log_format,
            colorize=False,
            backtrace=True,
            diagnose=True,
        )

        self.car_makers_file_path = os.path.join("resources", "car_makes.txt")
        if not os.path.exists(self.car_makers_file_path):
            logger.info("Manufacturers data not found. Fetching into resources/car_makes.txt")
            self._scrape_makes_models()

        self.models = self._read_models()
        self.ad_fetcher = AdvertisementFetcher()
        self.header = PAGE_HEADER
        pathlib.Path(self.data_directory).mkdir(parents=True, exist_ok=True)

    def _scrape_makes_models(self) -> None:
        """Function for scraping car manufacturers and car models.
        Inteded for single use when there is a need to update existing cars and models.
        """

        res = requests.get("https://www.otomoto.pl/ajax/jsdata/params/")
        data = res.text.split("var searchConditions = ")[1]
        data = data.split(";var searchCondition")[0]
        items = json.loads(data)
        source = items["values"]["573"]["571"]
        makes = list(source)

        results = {}

        resources_path = Path("resources/car_models")
        resources_path.mkdir(parents=True, exist_ok=True)

        for make in makes:
            results[make] = [model["value"] for model in source[make]]

            with open(resources_path.joinpath(str(make) + ".txt"), "w", encoding="utf-8") as models_file:
                for model in list(results[make]):
                    models_file.write(f"{model}\n")

        with open(self.car_makers_file_path, "w", encoding="utf-8") as maker_file:
            for maker in list(results.keys()):
                maker_file.write(f"{maker}\n")

    def _read_models(self):
        with open(self.car_makers_file_path, "r", encoding="utf-8") as file:
            models = file.readlines()
        return models

    def _get_cars_in_page(self, path, i):
        """
        Gets cars in page
        Args:
            path: path to page
            i: page number
        return:
            list of links
        """
        logger.info(f"Scrapping page: {i}")
        res = requests.get(f"{path}?page={i}", headers=self.header)
        soup = BeautifulSoup(res.content, "html.parser")
        car_links_section = soup.find("div", {"data-testid": "search-results"})
        links = []
        for x in car_links_section.find_all("div"):
            if articles := x.find("article", attrs={"data-media-size": True}):
                if articles_data := articles.find("a", href=True)["href"]:
                    links.append(articles_data)
        logger.info(f"Found {len(links)} links")
        return links

    def scrap_maker(self, model: str):
        """_summary_

        Args:
            model (str): name

        Raises:
            SystemExit: Error when obtaining HTTP request.
        """
        model = model.strip()
        logger.info(f"Start scrapping maker: {model}")
        path = f"https://www.otomoto.pl/osobowe/{model}"

        try:
            res = requests.get(path)
            res.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.info(f"Could not retrieve data from {path}.")
            logger.info(f"Error: {e}")
            raise SystemExit() from e

        soup = BeautifulSoup(res.text, features="lxml")
        if pagination_list_item := soup.find_all("li", attrs={"data-testid": "pagination-list-item"}):
            last_page_num = int(pagination_list_item[-1].text)
        else:
            last_page_num = 1

        last_page_num = min(last_page_num, 500)

        logger.info(f"Model has: {last_page_num} subpages")

        pages = range(1, last_page_num + 1)
        for page in tqdm(pages):
            links = self._get_cars_in_page(path, page)
            self.ad_fetcher.fetch_ads(links)
        self.ad_fetcher.save_ads(model)

        logger.info(f"End Scrapping model: {model}")

    def scrap_all_models(self):
        """Scrap all models listed in resources/car_makes.txt file"""
        logger.info("Starting scrapping cars...")
        for model in self.models:
            self.scrap_maker(model)
        logger.info("End scrapping cars")

    def combine_data(self, filename: str = "combined.csv") -> None:
        """Combine scrapped data into single csv file.

        Args:
            filename (str, optional): Name for the file with combined data. Defaults to 'combined.csv'.
        """
        logger.info("Combining data...")

        csv_files = [os.path.join(self.data_directory, file) for file in os.listdir(self.data_directory)]
        combined_data = []
        for csv_file in csv_files:
            combined_data.append(pd.read_csv(csv_file))
        df_all = pd.concat(combined_data, ignore_index=True)
        save_path = os.path.join(self.data_directory, filename)
        df_all.to_csv(save_path, index=False)
        logger.info(f"Combined data saved to {save_path}")
