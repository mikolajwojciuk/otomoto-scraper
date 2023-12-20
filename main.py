from modules.scrapers.car_scraper import CarScraper


if __name__ == "__main__":
    # car_scraper = CarScraper("resources/car_makes.txt", "output")
    car_scraper = CarScraper("output")

    # car_scraper.scrap_all_models()
    car_scraper.scrap_maker("alfa-romeo")
    # car_scraper.combine_data(filename="combined.csv")
