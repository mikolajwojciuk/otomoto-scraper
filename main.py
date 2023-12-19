from modules.scrapers.car_scraper import CarScraper


if __name__ == '__main__':
    car_scraper = CarScraper('resources/input/car_models.txt',
                             'output/data')
    #car_scraper.scrap_all_models()
    #car_scraper.scrap_model('abarth')
    #car_scraper.combine_data()
    import pandas as pd
    df = pd.read_csv('/Users/uzytkownik/Downloads/otomoto-scraper/Otomoto-Scraper/output/data/abarth.csv')
    print(df.head())