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

    df_joined['label'] = df_joined.apply(lambda row: f"{row['Player']} ({row['tag']})", axis=1)
    df_joined[['real_development', 'monthly_income', 'max_manpower']] =  df_joined[['real_development', 'monthly_income', 'max_manpower']].apply(pd.to_numeric)

    df_latest = df_joined.loc[df_joined.groupby('Player')['session'].idxmax()]

    player_tag_map = df_latest.set_index('Player')['tag'].to_dict()

    df_joined['tag'] = df_joined['Player'].map(player_tag_map)

    metric = st.selectbox(
    'What would you like to plot?',
    ('real_development', 'monthly_income', 'max_manpower'))

    st.markdown(
        """

    """
    )

    def get_latest_session_df(df):
        latest_session = df['session'].max()
        latest_session_df = df[df['session'] == latest_session]
        return(latest_session_df)
    
    def get_legend_order(df, metric):
        latest_df = get_latest_session_df(df)
        sorted_df = latest_df.sort_values(by=metric, ascending=False).set_index('tag')
        return(sorted_df)

    legend_order = get_legend_order(df_joined, metric)

    legend_selection = alt.selection_point(fields=['tag'], bind='legend')

    tag_to_hex = legend_order['hex'].to_dict()

    color_scale = alt.Scale(domain=list(tag_to_hex.keys()), range=list(tag_to_hex.values()))

    line_chart = alt.Chart(df_joined.reset_index()).mark_line().encode(
        x=alt.X('session:O', scale=alt.Scale(padding=0.1), axis=alt.Axis(labelAngle=0)),
        y=metric+':Q',
        opacity=alt.condition(legend_selection, alt.value(0.8), alt.value(0.2)),
        color=alt.Color('tag:N', scale=color_scale),
        tooltip=['tag:N']  
    ).interactive(
    ).add_params(legend_selection).properties(
    title=alt.TitleParams(
        text=f'{metric} over time'))

    st.altair_chart(line_chart, use_container_width=True)

    end_chart = alt.Chart(df_latest.reset_index()).mark_bar().encode(
        y=alt.Y('label:N', sort='-x'),#, scale=alt.Scale(padding=0.1), axis=alt.Axis(labelAngle=0)),
        x=metric+':Q',
        color=alt.Color('tag:N', scale=color_scale, legend=None),
        tooltip=['tag:N']  
    ).properties(
    title=alt.TitleParams(
        text=f'{metric} currently'))

    st.altair_chart(end_chart, use_container_width=True)

    df_joined.sort_values(by=['tag', 'session'], inplace=True)
    df_joined['lagged'] = df_joined.groupby('tag')[metric].shift(1)  # This creates the lagged column
    df_joined['session_diff'] = df_joined[metric] - df_joined['lagged']  # Calculate the difference
    latest_diff = df_joined.dropna().groupby('tag').last()
    
    diff_chart = alt.Chart(latest_diff.reset_index()).mark_bar().encode(
        y=alt.Y('label:N', sort='-x'),#, scale=alt.Scale(padding=0.1), axis=alt.Axis(labelAngle=0)),
        x='session_diff:Q',
        color=alt.Color('tag:N', scale=color_scale, legend=None),
        tooltip=['tag:N']  
    ).properties(
    title=alt.TitleParams(
        text=f'{metric} change this session'))
    
    st.altair_chart(diff_chart, use_container_width=True)


if __name__ == "__main__":
    run()
