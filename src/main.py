from modules.scrapers.car_scraper import CarScraper


if __name__ == "__main__":
    # If you have a list of specific car makes to scrape, you can pass it as a parameter.
    # car_scraper = CarScraper("resources/car_makes.txt", "output")

    # Create CarScraper instance with specified output.
    car_scraper = CarScraper("output")

    # car_scraper.scrap_all_makers()
    car_scraper.scrap_maker("marka_warszawa")
    # car_scraper.combine_data(filename="combined.csv")
