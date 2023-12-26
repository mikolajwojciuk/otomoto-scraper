# pylint: disable=C0301

import streamlit as st
import pandas as pd
import boto3
import os
from dotenv import load_dotenv


st.set_page_config(page_title="Otomoto analytics", page_icon="🚗", layout="wide")

if "s3" not in st.session_state:
    load_dotenv()

    region_name = os.environ["REGION_NAME"]
    aws_access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
    aws_secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]

    st.session_state.s3 = boto3.resource(
        service_name="s3",
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )

if "car_makes" not in st.session_state:
    car_makes_data = st.session_state.s3.Bucket("otomoto-scrapper-car-makes").Object("car_makes.txt").get()
    st.session_state.car_makes = pd.read_csv(car_makes_data["Body"], header=None)[0].to_list()


if "car_models" not in st.session_state:
    st.session_state.car_models = {}
    for make in st.session_state.car_makes:
        models_data = st.session_state.s3.Bucket("otomoto-scrapper-car-models").Object(f"car_models/{make}.txt").get()
        st.session_state.car_models[make] = pd.read_csv(models_data["Body"], header=None)[0].to_list()


st.title("Otomoto analytics")
st.subheader("Get insights from Otomoto")

st.divider()

n_makes_metric, n_models_metric = st.columns(2)

n_makes_metric.metric("Number of makes", str(len(st.session_state.car_makes)))
n_models_metric.metric(
    "Number of models", str(sum((len(st.session_state.car_models[make]) for make in st.session_state.car_makes)))
)


st.divider()
col1, col2 = st.columns([0.35, 0.65])

col1.text(
    """Select car brand to see
insights about it

You can also specify model
to get insights about it as well
          """
)

selected_make = col2.selectbox(
    label="Choose brand",
    options=st.session_state.car_makes,
    index=None,
    placeholder="Choose brand",
    label_visibility="collapsed",
)

if selected_make:
    selected_model = col2.selectbox(
        label="Choose model",
        options=["All models"] + st.session_state.car_models[selected_make],
        index=0,
        placeholder="Choose model",
        label_visibility="collapsed",
    )

st.markdown(
    """<div style="width:100%;text-align:center;">
    Developed by Mikołaj Wojciuk
    <a href="https://www.linkedin.com/in/mikołaj-wojciuk-72956a20b" style="float:center">
    <img src="https://content.linkedin.com/content/dam/me/business/en-us/amp/brand-site/v2/bg/LI-Bug.svg.original.svg" width="22px"></img></a>
    </div>""",
    unsafe_allow_html=True,
)
