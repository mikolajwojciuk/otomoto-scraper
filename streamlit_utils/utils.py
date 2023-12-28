# pylint: disable=W9011
import pandas as pd
import numpy as np
from typing import List
import boto3
from botocore.exceptions import ClientError
import streamlit as st
from dotenv import load_dotenv
import os


@st.cache_resource(show_spinner=False)
def get_session_state() -> tuple[boto3.s3, list, dict]:
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


def get_maker_data(s3_resource: boto3.s3, maker: str) -> pd.DataFrame:
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
