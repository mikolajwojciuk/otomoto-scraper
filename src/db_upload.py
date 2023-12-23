from utils.db_utils import upload_to_db
from glob import glob
import os

files_to_upload = glob(os.getcwd() + "/output/data/*.csv")
upload_to_db(csv_files=files_to_upload, features=os.getcwd() + "/src/resources/features_names.txt")
