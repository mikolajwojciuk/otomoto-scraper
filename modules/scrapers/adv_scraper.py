import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from loguru import logger

import pandas as pd
import requests
from bs4 import BeautifulSoup
from resources.headers import ADVERT_HEADERS


class AdvertisementFetcher:
    """
    Fetches advertisements
    Args:
         features_file_path: Path to file with features
    """

    MAX_THREADS = 8

    def __init__(self, features_file_path="resources/features_names.txt"):
        self.features_file_path = os.path.join(os.getcwd(), features_file_path)
        self.all_features = self._read_features()
        self.header = random.choice(ADVERT_HEADERS)
        self.cars = []

    def _read_features(self) -> List[str]:
        with open(self.features_file_path, "r", encoding="utf-8") as feats_file:
            features = feats_file.readlines()
        return [x.strip() for x in features]

    def _make_line(self, main_features) -> Dict[str, str]:
        temp = {feat: main_features.get(feat, None) for feat in self.all_features}
        return temp

    def _download_url(self, path) -> Optional[Dict[str, str]]:
        try:
            res = requests.get(path)
            res.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.info(f"Could not retrieve data from {path}.")
            logger.info(f"Error: {e}")
            logger.info(f"Skipping {path} url.")
            return None

        soup = BeautifulSoup(res.text, features="lxml")
        if style_tags := soup.find_all("style"):
            for style_tag in style_tags:
                style_tag.decompose()

        features = self._get_main_features(soup)
        extendend_features = self._get_extended_features(path, soup)
        features.update(extendend_features)
        price_feat = self._get_price(soup)
        features.update(price_feat)
        currency_feat = self._get_currency(soup)
        features.update(currency_feat)
        features.update({"Url": str(path)})
        features = self._make_line(features)

        return features

    def _get_main_features(self, soup) -> Dict[str, str]:
        features = {}
        if main_params := soup.find("div", {"data-testid": "content-details-section"}):
            if advert_details := main_params.find_all("div", attrs={"data-testid": "advert-details-item"}):
                for param in advert_details:
                    el = [x.text for x in param]
                    features.update({el[0]: el[1]})

        else:
            if main_params := soup.find_all(class_="offer-params__item"):
                features = {
                    param.find("span", class_="offer-params__label")
                    .text.strip(): param.find("div", class_="offer-params__value")
                    .text.strip()
                    for param in main_params
                }

        return features

    def _get_extended_features(self, path, soup) -> Dict[str, str]:
        features = {}

        try:
            extendend_params = soup.find_all("div", attrs={"data-testid": "accordion-collapse-inner-content"})
            for param in extendend_params:
                for x in param.find_all("p"):
                    features[x.text.strip()] = 1
        except (IndexError, AttributeError) as e:
            logger.info(
                f"""Error while fetching extended features using accordion-collapse-inner-content: {e}.
                Processing with parameter-feature-item"""
            )
            try:
                extendend_params = soup.find_all("li", class_="parameter-feature-item")
                for param in extendend_params:
                    features[param.text.strip()] = 1
            except (IndexError, AttributeError) as ee:
                logger.info(f"Error {ee} while fetching extended features from {path}")
        return features

    def _get_price(self, soup) -> Dict[str, str]:
        features = {}
        try:
            price = "".join(soup.select('h3[class^="offer-price__number"]')[0].text.strip().split())
            features["Cena"] = price
        except (IndexError, AttributeError) as e:
            logger.info(
                f"""Error while fetching price feature from h3 offer-price__number: {e}.
            Processing with span offer-price__number"""
            )
            try:
                price = "".join(soup.find("span", class_="offer-price__number").text.strip().split()[:-1])
                features["Cena"] = price
            except (IndexError, AttributeError) as ee:
                logger.info(f"Error {ee} while fetching price feature.")
                features["Cena"] = None
        return features

    def _get_currency(self, soup) -> Dict[str, str]:
        features = {}

        try:
            currency = "".join(soup.select('p[class^="offer-price__currency"]')[0].text.strip().split())
            features["Waluta"] = currency
        except (IndexError, AttributeError) as e:
            logger.info(
                f"""Error while fetching currency feature from p offer-price__currency: {e}.
            Processing with span offer-price__currency"""
            )
            try:
                currency = soup.find("span", class_="offer-price__currency").text.strip()
                features["Waluta"] = currency
            except (IndexError, AttributeError) as ee:
                logger.info(f"Error {ee} while fetching currency feature.")
                features["Waluta"] = None
        return features

    def fetch_ads(self, links: List[str]):
        """Fetches ads
        Args:
             links(list[str]): links
        """
        with ThreadPoolExecutor(max_workers=min(self.MAX_THREADS, len(links) + 1)) as executor:
            features = []
            for link in links:
                features.append(executor.submit(self._download_url, link))
            for feature in as_completed(features):
                result = feature.result()
                if result is not None and result["Cena"] is not None:
                    self.cars.append(result)

    def save_ads(self, model: str):
        """
        Saves ads
        Args:
             model(str): model
        """

        pd.DataFrame(self.cars).to_csv(f"output/data/{model}.csv", index=False)
