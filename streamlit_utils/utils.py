# pylint: disable=W9011
import pandas as pd
import numpy as np
from typing import List
import boto3
from botocore.exceptions import ClientError
import streamlit as st
from dotenv import load_dotenv
import os
from sklearn.model_selection import RandomizedSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from sklearn.compose import ColumnTransformer


@st.cache_resource(show_spinner=False)
def get_session_state() -> tuple:
    """Prepare S3 session, list of car makes and dict of car models for streamlit session state

    Returns:
        tuple[boto3.s3, list, dict]: Tuple with S3 session, list of car makes and dict of car models
    """
    # Preparing access to S3 resources
    load_dotenv()
    region_name = os.environ["REGION_NAME"]
    aws_access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
    aws_secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]
    s3 = boto3.resource(
        service_name="s3",
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )

    # Preparing data on car makes
    car_makes_data = s3.Bucket("otomoto-scrapper-car-makes").Object("car_makes.txt").get()
    car_makes = pd.read_csv(car_makes_data["Body"], header=None, low_memory=False)[0].to_list()

    # Preparing data on car models
    car_models = {}
    for make in car_makes:
        models_data = s3.Bucket("otomoto-scrapper-car-models").Object(f"car_models/{make}.txt").get()
        car_models[make] = pd.read_csv(models_data["Body"], header=None, low_memory=False)[0].to_list()

    return s3, car_makes, car_models


def get_maker_data(s3_resource, maker: str) -> pd.DataFrame:
    """Function for downloading data on single car manufacturer

    Args:
        s3_resource (s3): Instance of boto3 resource with s3 service
        maker (str): Name of the maker

    Returns:
        pd.DataFrame: Dataframe with maker data
    """

    @st.cache_data(show_spinner=False)
    def download_maker_data(maker: str) -> pd.DataFrame:
        try:
            maker_data = s3_resource.Bucket("otomoto-scrapper").Object(f"{maker}.txt").get()
            maker_data = pd.read_csv(maker_data["Body"], low_memory=False)
            return maker_data
        except ClientError as e:
            if not e.response["Error"]["Code"] == "NoSuchKey":
                raise
            return pd.DataFrame()

    return download_maker_data(maker)


@st.cache_data(show_spinner=False)
def process_data(data: pd.DataFrame) -> pd.DataFrame:
    """Function for processing data for streamlit app

    Args:
        data (pd.DataFrame): Input dataframe with scrapped data on single car manufacturer.

    Returns:
        pd.DataFrame: Processed data
    """

    # Price processing
    data["Cena"] = data["Cena"].astype(str).str.replace(",", ".").astype(float)

    # Mileage processing
    data.dropna(subset=["Przebieg"], inplace=True)
    data["Przebieg"] = (
        data["Przebieg"].astype(str).apply(lambda x: (x.replace("km", "").replace(" ", ""))).astype(float)
    )

    # Power processing
    data.dropna(subset=["Moc"], inplace=True)
    data["Moc"] = data["Moc"].astype(str).apply(lambda x: (x.replace("KM", "").replace(" ", ""))).astype(float)

    # Production year processing
    data.dropna(subset=["Rok produkcji"], inplace=True)

    return data


@st.cache_resource(show_spinner=False)
def smoothen_plot(data: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """Function for fitting exponential decay to the column data in order to generate smooth plot from it.

    Args:
        data (pd.DataFrame): Input dataframe with columns with missing/noisy data to smoothen.
        columns (List[str]): List of names of columns to process.
    Returns:
        pd.DataFrame: Dataframe extended by columns with extrapolated data
    """
    coeffs_array = []
    x = data["Przebieg"].to_numpy()
    for column in columns:
        y = data[column].to_numpy()
        idx = np.isfinite(x) & np.isfinite(y)
        coeffs = np.polyfit(x[idx], np.log(y[idx]), 1)
        coeffs_array.append(coeffs)

    coeffs_array = np.array(coeffs_array)

    for coeff, column in zip(coeffs_array, columns):
        if not ((np.abs(coeff - coeffs_array.mean(axis=0))) > 2 * coeffs_array.std(axis=0)).any():
            if len(data) - data[column].isna().sum() > 1:
                data[column] = np.exp(np.polyval(coeff, x))

    return data


def estimate_price(feature_dict: dict, data: pd.DataFrame) -> float:
    """Function for estimating price of a car based on its features.

    Args:
        feature_dict (dict): Dictionary with car features (keys) and their values.
        data (pd.DataFrame): Processed dataframe with car data.
    """
    columns_to_drop = [
        "Marka pojazdu",
        "Model pojazdu",
        "Kraj pochodzenia",
        "Stan",
        "Waluta",
        "Url",
        "Oferta od",
        "Pojemność skokowa",
        "Rodzaj koloru",
    ]
    columns_min_max = ["Rok produkcji", "Przebieg", "Moc"]
    columns_one_hot = ["Rodzaj paliwa", "Skrzynia biegów", "Napęd", "Typ nadwozia", "Kolor"]
    binary_columns_to_drop = [
        column
        for column in data.select_dtypes(include=["float64"]).columns.to_list()
        if column not in ["Hak", "Bezwypadkowy", "Cena", "Przebieg", "Moc"]
    ]

    data = data.drop(binary_columns_to_drop, axis=1)
    data = data.drop(columns_to_drop, axis=1)
    # data = process_data(data)

    target = data["Cena"]
    data.drop(["Cena"], axis=1, inplace=True)
    features = data.drop([column for column in data.columns if column not in feature_dict.keys()], axis=1)

    print(features.columns)

    for column in features.columns:
        if features[column].isna().sum() > 0:
            features[column].fillna(features[column].value_counts().index[0], inplace=True)

    transformers = [
        ("num", "passthrough", features.select_dtypes(exclude=["object"]).columns),
        ("cat", OneHotEncoder(), columns_one_hot),
        ("min_max", MinMaxScaler(), columns_min_max),
    ]

    preprocessor = ColumnTransformer(transformers=transformers)
    features = preprocessor.fit_transform(features)

    model = RandomForestRegressor(random_state=2137)

    param_dist = {
        "n_estimators": [50, 100],
        "max_depth": [None, 10, 20],
        "min_samples_split": [2, 5],
        "min_samples_leaf": [1, 2, 4],
    }

    random_search = RandomizedSearchCV(
        model, param_distributions=param_dist, n_iter=5, cv=2, scoring="neg_mean_squared_error", random_state=2137
    )
    random_search.fit(features, target)

    prediction_features = preprocessor.transform(pd.DataFrame([feature_dict]))
    result = int(random_search.predict(prediction_features))
    result -= result % 100

    return result
