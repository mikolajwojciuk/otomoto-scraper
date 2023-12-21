from typing import List, Union
import os
from dotenv import load_dotenv
import pandas as pd
import pymongo
from tqdm.auto import tqdm, trange


def upload_to_db(csv_files: List[str], features: Union[List[str], str], db_name: str = "otomoto-scraper") -> None:
    """Function for uploading scraped csv files to MongoDB database

    Args:
        csv_files (List[str]): List of csv files.
        features (Union[List[str],str]): List of features or path to text file with features.
        db_name (str): Name of the database to which data will be uploaded.

    Raises:
        TypeError: Error when provided features do not match expected format.
    """

    if not isinstance(features, list):
        if os.path.isfile(features):
            with open(features, "r", encoding="utf-8") as feats_file:
                features = feats_file.readlines()
            features = [x.strip() for x in features]
        else:
            raise TypeError("Provided features should be a list of strings or path to text file.")

    load_dotenv()
    connection_string = os.environ["CONNECTION_STRING"]
    client = pymongo.MongoClient(connection_string)
    db = client[db_name]

    progress_bar = trange(len(csv_files))
    for n in progress_bar:
        collection_name = os.path.split(csv_files[n])[1].split(".")[0]
        tqdm.write(f"Uploading {collection_name} data...")

        data = pd.read_csv(csv_files[n])[features]
        processed_data = _process_dataframe(data)
        processed_data = processed_data.to_dict(orient="records")

        collection = db[collection_name]
        collection.insert_many(processed_data)


def _process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Process dataframe in order to meet MongoDB requirements.

    Args:
        df (pd.DataFrame): DataFrame to be processed

    Returns:
        pd.DataFrame: Processed DataFrame
    """

    df.reset_index(inplace=True)
    df.columns = df.columns.str.replace(",", "")

    return df
