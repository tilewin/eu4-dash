import streamlit as st
from streamlit.logger import get_logger
import requests
import pandas as pd
import altair as alt
from typing import Dict, List

LOGGER = get_logger(__name__)

# Constants
API_KEY = "088e8c167dd8cd1734faf8cdaa761d5d"
API_URL = "https://skanderbeg.pm/api.php"
EDIT_URL = "https://docs.google.com/spreadsheets/d/1h_fxzkHicBAAtWn3QO_apuvdIXeJP98e1R86RUN4xv4/edit?usp=sharing"
DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSXz-17mvdL20ECgzpxGznrUCXqlxm7zz-wOoYdQPg9pi4tQe_ApctCroah-m3FPFP825ejaoLfL5zp/pub?gid=0&single=true&output=csv"
METRICS = ["real_development", "monthly_income", "max_manpower"]

@st.cache_data
def get_data(params: Dict[str, str], saves: List[str]) -> pd.DataFrame:
    """
    Fetch data from the API for each save and combine into a single DataFrame.
    """
    dfs = []

    for i, save in enumerate(saves):
        params["save"] = save
        try:
            with requests.get(API_URL, params=params) as response:
                response.raise_for_status()
                data = response.json()
                df = pd.concat([pd.DataFrame(v) for v in data.values()])
                df['session'] = i
                dfs.append(df)
        except requests.RequestException as e:
            LOGGER.error(f"Error fetching data for save {save}: {e}")

    df = pd.concat(dfs, ignore_index=True)
    df.set_index('tag', inplace=True)
    return df

def process_sessions_data(df_sessions: pd.DataFrame) -> pd.DataFrame:
    """
    Process the sessions data by dropping empty columns and forward-filling values.
    """
    columns_to_drop = df_sessions.columns[df_sessions.iloc[0].isna()]
    return df_sessions.drop(columns=columns_to_drop).ffill(axis=1)

def get_saves(df_sessions: pd.DataFrame) -> List[str]:
    """
    Extract save IDs from the sessions DataFrame.
    """
    return df_sessions.iloc[0].tolist()[1:]

def prepare_joined_data(df_sessions: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare joined data by merging sessions and API data.
    """
    df_sessions_long = df_sessions.melt(id_vars=['Player'], 
                                        var_name='session', 
                                        value_name='tag')
    df_sessions_long['session'] = df_sessions_long['session'].str.extract('(\d+)').astype(int)
    df_joined = pd.merge(df_sessions_long, df, on=['session', 'tag'], how='inner')
    df_joined['label'] = df_joined.apply(lambda row: f"{row['Player']} ({row['tag']})", axis=1)
    df_joined[METRICS] = df_joined[METRICS].apply(pd.to_numeric)
    
    # Update tags to latest for each player
    df_latest = df_joined.loc[df_joined.groupby('Player')['session'].idxmax()]
    player_tag_map = df_latest.set_index('Player')['tag'].to_dict()
    df_joined['tag'] = df_joined['Player'].map(player_tag_map)
    return df_joined

def get_latest_session_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get the DataFrame for the latest session.
    """
    latest_session = df['session'].max()
    return df[df['session'] == latest_session]

def get_legend_order(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """
    Get the legend order based on the latest session data.
    """
    latest_df = get_latest_session_df(df)
    return latest_df.sort_values(by=metric, ascending=False).set_index('tag')

def create_line_chart(df: pd.DataFrame, metric: str, color_scale: alt.Scale) -> alt.Chart:
    """
    Create a line chart for the given metric.
    """
    legend_selection = alt.selection_point(fields=['tag'], bind='legend')
    return alt.Chart(df.reset_index()).mark_line().encode(
        x=alt.X('session:O', scale=alt.Scale(padding=0.1), axis=alt.Axis(labelAngle=0)),
        y=f'{metric}:Q',
        opacity=alt.condition(legend_selection, alt.value(0.8), alt.value(0.2)),
        color=alt.Color('tag:N', scale=color_scale),
        tooltip=['tag:N']  
    ).interactive().add_params(legend_selection).properties(
        title=alt.TitleParams(text=f'{metric} over time')
    )

def create_diff_chart(df: pd.DataFrame, metric: str, color_scale: alt.Scale) -> alt.Chart:
    """
    Create a bar chart showing the difference in metric for the latest session.
    """
    df = df.sort_values(by=['tag', 'session'])
    df['lagged'] = df.groupby('tag')[metric].shift(1)
    df['session_diff'] = df[metric] - df['lagged']
    latest_diff = df.groupby('tag').last()
    return alt.Chart(latest_diff.reset_index()).mark_bar().encode(
        y=alt.Y('label:N', sort='-x'),
        x='session_diff:Q',
        color=alt.Color('tag:N', scale=color_scale, legend=None),
        tooltip=['tag:N']  
    ).properties(
        title=alt.TitleParams(text=f'{metric} change this session')
    )

def create_pct_change_chart(df: pd.DataFrame, metric: str, color_scale: alt.Scale) -> alt.Chart:
    """
    Create a bar chart showing the percentage change in metric for the latest session.
    """
    df = df.sort_values(by=['tag', 'session'])
    df['lagged'] = df.groupby('tag')[metric].shift(1)
    df['session_pct_change'] = ((df[metric] - df['lagged']) / df['lagged']) * 100
    latest_pct_change = df.groupby('tag').last()
    return alt.Chart(latest_pct_change.reset_index()).mark_bar().encode(
        y=alt.Y('label:N', sort='-x'),
        x='session_pct_change:Q',
        color=alt.Color('tag:N', scale=color_scale, legend=None),
        tooltip=['tag:N']  
    ).properties(
        title=alt.TitleParams(text=f'{metric} percentage change this session')
    )

def create_end_chart(df: pd.DataFrame, metric: str, color_scale: alt.Scale) -> alt.Chart:
    """
    Create a bar chart showing the current metric values.
    """
    return alt.Chart(df.reset_index()).mark_bar().encode(
        y=alt.Y('label:N', sort='-x'),
        x=f'{metric}:Q',
        color=alt.Color('tag:N', scale=color_scale, legend=None),
        tooltip=['tag:N']  
    ).properties(
        title=alt.TitleParams(text=f'{metric} currently')
    )

def run():
    """
    Main function to run the Streamlit app.
    """
    st.set_page_config(page_title="EU4 Twitter Dashboard", page_icon="🗡️")
    st.write("# EU4 Twitter Dashboard")

    st.markdown(f"The sheet that drives this dashboard is [here]({EDIT_URL}). "
                "If there's a new Skanderbeg save ID, or if you've changed tag, feel free to add it there.")

    df_sessions = process_sessions_data(pd.read_csv(DATA_URL))
    saves = get_saves(df_sessions)

    params = {
        "key": API_KEY,
        "value": "player;was_player;tag;hex;monthly_income;total_development;real_development;max_manpower;FL",
        "scope": "getCountryData",
        "format": "json",
        "save": "None"
    }

    df = get_data(params, saves)

    df_joined = prepare_joined_data(df_sessions, df)

    metric = st.selectbox('What would you like to plot?', METRICS)

    legend_order = get_legend_order(df_joined, metric)
    tag_to_hex = legend_order['hex'].to_dict()
    color_scale = alt.Scale(domain=list(tag_to_hex.keys()), range=list(tag_to_hex.values()))

    line_chart = create_line_chart(df_joined, metric, color_scale)
    st.altair_chart(line_chart, use_container_width=True)

    diff_chart = create_diff_chart(df_joined, metric, color_scale)
    st.altair_chart(diff_chart, use_container_width=True)

    pct_change_chart = create_pct_change_chart(df_joined, metric, color_scale)
    st.altair_chart(pct_change_chart, use_container_width=True)

    df_latest = df_joined.loc[df_joined.groupby('Player')['session'].idxmax()]
    end_chart = create_end_chart(df_latest, metric, color_scale)
    st.altair_chart(end_chart, use_container_width=True)

if __name__ == "__main__":
    run()