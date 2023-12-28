import pandas as pd
import numpy as np
from typing import List


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


def smoothen_plot(data: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """Function for fitting polynomial to the column data in order to generate smooth plot from it.

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
            data[column] = np.exp(np.polyval(coeff, x))

    return data
