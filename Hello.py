# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import streamlit as st
from streamlit.logger import get_logger
import requests
import polars as pl
import pandas as pd

LOGGER = get_logger(__name__)

params = {
    "key": "088e8c167dd8cd1734faf8cdaa761d5d",
    "value": "player;was_player;tag;hex;monthly_income;total_development;real_development;max_manpower;FL",
    "scope": "getCountryData",
    "format": "json",
    "save": "e0351f"
}

@st.cache_data
def get_data(params):
    response = requests.get("https://skanderbeg.pm/api.php", params=params)
    d = response.json()
    df = pd.concat([pd.DataFrame(v) for k,v in d.items()])
    df.set_index('tag', inplace=True)
    return df



def run():
    st.set_page_config(
        page_title="Hello",
        page_icon="👋",
    )

    st.write("# Welcome to Streamlit! 👋")

    df = get_data(params)

    df

    st.markdown(
        """
        asd
    """
    )


if __name__ == "__main__":
    run()
