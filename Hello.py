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
import pandas as pd
import altair as alt

LOGGER = get_logger(__name__)

params = {
    "key": "088e8c167dd8cd1734faf8cdaa761d5d",
    "value": "player;was_player;tag;hex;monthly_income;total_development;real_development;max_manpower;FL",
    "scope": "getCountryData",
    "format": "json",
    "save": "None"
}

# todo: pull this out so we can have a link for each sheet, published individually
edit_url = "https://docs.google.com/spreadsheets/d/1h_fxzkHicBAAtWn3QO_apuvdIXeJP98e1R86RUN4xv4/edit?usp=sharing"
data_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSXz-17mvdL20ECgzpxGznrUCXqlxm7zz-wOoYdQPg9pi4tQe_ApctCroah-m3FPFP825ejaoLfL5zp/pub?output=csv"
df_sessions = pd.read_csv(data_url)


#saves = ["1d6ea5", "e243dc", "b84952"]

@st.cache_data
def get_data(params, saves):
    dfs = []

    for save in saves:
        params["save"] = save
        response = requests.get("https://skanderbeg.pm/api.php", params=params)
        d = response.json()
        df = pd.concat([pd.DataFrame(v) for k,v in d.items()])
        dfs.append(df)

    for i, df in enumerate(dfs):
        df['session'] = i

    df = pd.concat(dfs, ignore_index=True)
    df.set_index('tag', inplace=True)
    return df

def run():
    st.set_page_config(
        page_title="EU4 Twitter Dashboard",
        page_icon="🗡️",
    )

    st.write("# EU4 Twitter Dashboard")

    df_sessions
    saves = df_sessions[df_sessions['Player'].isna()].dropna(axis=1).iloc[0].tolist()
    
    st.markdown(
        """
        Select the tags you'd like to include, and the metric you'd like to plot.
        
        To see a specific tag, you can click on the plot's legend to show it more clearly. Click anywhere on the plot to return to showing all tags.
        
        This is the early beta version, please WhatsApp me with any suggestions!
    """
    )
    df = get_data(params, saves)

    all_tags = df.index.unique().tolist()
    player_tags = df.query('was_player == "Yes"').index.unique().tolist()

    

    #options = st.multiselect(
    #'What Skanderbeg IDs should be used?',
    #all_tags,
    #player_tags)

    tags = st.multiselect(
    'What tags should be included?',
    all_tags,
    player_tags)

    df_tags = df.loc[tags]

    metric = st.selectbox(
    'What would you like to plot?',
    ('real_development', 'monthly_income', 'max_manpower'))

    legend_selection = alt.selection_point(fields=['tag'], bind='legend')

    tag_to_hex = df.loc[tags]['hex'].to_dict()

    color_scale = alt.Scale(domain=list(tag_to_hex.keys()), range=list(tag_to_hex.values()))

    chart = alt.Chart(df_tags.reset_index()).mark_line().encode(
        x=alt.X('session:O', scale=alt.Scale(padding=0.1), axis=alt.Axis(labelAngle=0)),
        y=metric+':Q',
        opacity=alt.condition(legend_selection, alt.value(0.8), alt.value(0.2)),
        color=alt.Color('tag:N', scale=color_scale),
        tooltip=['tag:N']  
    ).interactive(
    ).add_params(legend_selection)


    st.altair_chart(chart, use_container_width=True)


if __name__ == "__main__":
    run()
