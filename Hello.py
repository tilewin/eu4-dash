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
data_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSXz-17mvdL20ECgzpxGznrUCXqlxm7zz-wOoYdQPg9pi4tQe_ApctCroah-m3FPFP825ejaoLfL5zp/pub?gid=0&single=true&output=csv"
df_sessions = pd.read_csv(data_url)

columns_to_drop = df_sessions.columns[df_sessions.iloc[0].isna()]

# explain the col dropping logic as well as how ffill works
df_sessions = df_sessions.drop(columns=columns_to_drop).fillna(method='ffill', axis=1)



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

    # for this, we want to write a function that maps each tag 
    # forward until it meets a replacement
    # then we join on session and tag, then pull as the label
    # Player + Latest tag
    # We'll probably need to go backward and rewrite player and tag in the table

    # to get saves we take the first row, remove the nas, then remove the session_id col
    # we should roll na removal based on the session column into the table

    

    # pull this into an explainable function
    saves = df_sessions.iloc[0].tolist()[1:]
    
    st.markdown(
        """
        The sheet that drives this dashboard is [here](https://docs.google.com/spreadsheets/d/1h_fxzkHicBAAtWn3QO_apuvdIXeJP98e1R86RUN4xv4/edit?usp=sharing). 
        If there's a new Skanderbeg save ID, or if you've changed tag, feel free to add it there.
    """
    )
    df = get_data(params, saves)

    df_sessions_long = df_sessions.melt(id_vars=['Player'], 
                # this is too specific and needs to be generalised to other columns
                  var_name='session', 
                  value_name='tag')

    # Convert 'Session' to integer
    df_sessions_long['session'] = df_sessions_long['session'].str.extract('(\d+)').astype(int)

    df_joined = pd.merge(df_sessions_long, df, on=['session', 'tag'], how='inner')

    # replace tag and hex with the max values for each player

    latest_tag = df_joined.loc[df_joined.groupby('Player')['session'].idxmax()]
    
    player_tag_map = latest_tag.set_index('Player')['tag'].to_dict()

    df_joined['tag'] = df_joined['Player'].map(player_tag_map)

    tags =  df_joined['tag'].unique().tolist()

    metric = st.selectbox(
    'What would you like to plot?',
    ('real_development', 'monthly_income', 'max_manpower'))

    legend_selection = alt.selection_point(fields=['tag'], bind='legend')

    tag_to_hex = df.loc[tags]['hex'].to_dict()

    color_scale = alt.Scale(domain=list(tag_to_hex.keys()), range=list(tag_to_hex.values()))

    chart = alt.Chart(df_joined.reset_index()).mark_line().encode(
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
