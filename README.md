# Otomoto-Scraper
App developed to provide insights from polish used car market website [Otomoto](https://www.otomoto.pl).
Demo can be found [here](https://otomoto-analytics.streamlit.app).

Code contains 3 main parts:
 - [scrapers](https://github.com/mikolajwojciuk/otomoto-scraper/tree/main/src/modules/scrapers)
 - [data processing](https://github.com/mikolajwojciuk/otomoto-scraper/blob/main/src/utils/db_utils.py)
 - [streamlit app](https://github.com/mikolajwojciuk/otomoto-scraper/blob/main/app.py)


## Usage

### Installation
In order to use the code, make sure to use virtual environment:
```bash
python -m venv/venv
source venv/bin/activate
```
Install requirements:
```bash
pip install -r requirements.txt
```

### Scraping
In order to scrap all available data, run:
```bash
python src/main.py
```
If needed, You can also scrap data on individual car makers: see **src/main.py** and modify it according to Your needs, following provided instructions.


**NOTE:** This process can take a long time, depending on number of cars available on website. Progress can be tracked in terminal.

### Uploading data to S3
Demo app is designed to work with data stored in AWS S3 bucket. In order to upload data to S3, make sure it have been downloaded. You also have to create **.env** file, following the provided **.env_template**.
Script for uploading data to S3 can be found [here](https://github.com/mikolajwojciuk/otomoto-scraper/blob/main/src/db_upload.py). When using it, make sure to provide correct bucket name in **upload_to_db** function.


### Demo
Demo for this app was created using streamlit. You can check it out using link provided above.
If You want to run it locally, run:
```bash
streamlit run app.py
```

**NOTE:** This app was not designed to be used in production. It was created for educational purposes. It might require further development and running it locally will require access to data stored in S3 bucket as well as accordingly modifyied bucket names in streamlit_utils/utils.py file.