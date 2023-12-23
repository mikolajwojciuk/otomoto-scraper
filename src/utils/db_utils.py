from typing import List, Union
import os
from dotenv import load_dotenv
import pandas as pd
import pymongo
from tqdm.auto import tqdm, trange

pd.options.mode.chained_assignment = None  # Disable Pandas SettingWithCopyWarning


def upload_to_db(
    csv_files: List[str], features: Union[List[str], str], min_n_records: int = 100, db_name: str = "otomoto-scraper"
) -> None:
    """Function for uploading scraped csv files to MongoDB database

    Args:
        csv_files (List[str]): List of csv files.
        features (Union[List[str],str]): List of features or path to text file with features.
        min_n_records (int): Minimum number of records for car model for it to be uploaded. Defaults to 100.
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

        data = pd.read_csv(csv_files[n], low_memory=False)[features]
        processed_data = _process_dataframe(data, min_n_records)
        if not processed_data.empty:
            tqdm.write(f"Uploading {collection_name} data...")
            processed_data = processed_data.to_dict(orient="records")
            collection = db[collection_name]
            collection.insert_many(processed_data)
        else:
            tqdm.write(
                f"Skipping uploading {collection_name} data - no model meets minimum number of records condition."
            )


def _process_dataframe(df: pd.DataFrame, min_n_records: int) -> pd.DataFrame:
    """Process dataframe in order to meet MongoDB requirements.

    Args:
        df (pd.DataFrame): DataFrame to be processed
        min_n_records (int): Minimum number of records for car model for it to be uploaded.

    Returns:
        pd.DataFrame: Processed DataFrame
    """

    df.reset_index(inplace=True)
    df.columns = df.columns.str.replace(",", "")
    df = df[df.groupby("Model pojazdu")["Model pojazdu"].transform("size") >= min_n_records]
    df.drop(
        columns=[
            "Wersja",
            "Pokaż oferty z numerem VIN",
            "Kategoria",
            "Generacja",
            "Emisja CO2",
            "Rodzaj własności baterii",
            "Pojemność baterii",
            "Spalanie W Mieście",
            "Metalik",
            "Leasing",
            "VAT marża",
            "Faktura VAT",
            "Okres gwarancji producenta",
            "Możliwość finansowania",
            "Pierwsza rejestracja",
            "Pierwszy właściciel",
            "Ma numer rejestracyjny",
            "Autonomia",
        ],
        inplace=True,
    )

    binary_str_columns = [
        "Kierownica po prawej (Anglik)",
        "Zarejestrowany w Polsce",
        "Bezwypadkowy",
        "Serwisowany w ASO",
    ]

    for column_name in binary_str_columns:
        df.loc[df[column_name] == "Tak", column_name] = 1.0
        df[column_name].fillna(0.0, inplace=True)

    binary_columns = [
        column
        for column in df.columns
        if ((df[column].nunique() == 1 or df[column].nunique() == 0) and df[column].dtype == "float64")
    ]

    for column in binary_columns:
        df[column].fillna(0.0, inplace=True)
    return df
