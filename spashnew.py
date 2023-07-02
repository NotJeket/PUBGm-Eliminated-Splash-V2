from dash import *
from collections import deque
from dash.dependencies import Output, Input, State
import json,threading,time,requests
import pandas as pd

external_stylesheets = ['assets/style.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, serve_locally=True)

# Initialize lock for team data
team_data_lock = threading.Lock()

def get_font_size(name):
    name_length = len(name)
    if name_length <= 6:
        return "30px"
    elif name_length <= 11:
        return "25px"
    else:
        return "20px"
#Prestige Gaming
# Define function to read in url and return data as a DataFrame
def read_json_data_from_api(api_url):
    response = requests.get(api_url)
    if response.status_code == 200:
        json_data = response.json()
        team_data = pd.json_normalize(json_data["allinfo"]["TeamInfoList"])
        player_data = pd.json_normalize(json_data["allinfo"]["TotalPlayerList"])
        rank_data = player_data.groupby("teamName")["rank"].first().reset_index()
        team_data = pd.merge(team_data, rank_data, on="teamName")
        return team_data
    else:
        raise ValueError("Failed to retrieve data from API")

# Initialize team_data with the initial data from API
with team_data_lock:
    team_data = read_json_data_from_api("http://127.0.0.1:5000/data1")

#http://192.168.100.197:10086/getallinfo
def generate_splash_screen(team, start_time):
    with team_data_lock:
        team_data_row = team_data[team_data["teamName"] == team].iloc[0]
        rank = team_data_row["rank"]
        kills = team_data_row["killNum"]

    elapsed_time = time.time() - start_time
    if elapsed_time > 10:
        return None  # Hide the splash screen after 10 seconds

    font_size = get_font_size(team)
    return html.Div(
        [
            html.Div(
                [
                    html.Img(src=f"/assets/logos/{team}.png", className="team-logo"),
                ],
                className="team-logo-container",
            ),
            html.Div(
                [
                    html.Div("ELIMINATED", className="team-info"),
                    html.Div(
                        team,
                        className="team-name",
                        style={
                            'font-size': font_size
                        }
                    ),
                    html.Div([html.Div(f" ELIMS {kills}", className="team-kills"),
                              html.Div(f"{rank}/16", className="team-rank")], className="team-info-row"),
                ],
                className="splash-screen-container",
            ),
        ],
        className=f"splash-screen {'fade-out' if elapsed_time > 8 else 'fade-in'}",
        id="splash-screen",
        style={'background-image': 'url("/assets/images/test.png")', 'background-size': 'cover',
               "object-fit": "contain"}
    )


app.layout = html.Div(
    [
        html.H1(""),
        html.Div(id="splash-screen-container"),
        dcc.Interval(
            id='interval-component',
            interval=2*1000, # update every 2 seconds
            n_intervals=0
        )
    ]
)

# Initialize queue to store order of dead teams
dead_teams_queue = deque()
# Initialize set to store teams that have already been displayed
displayed_teams = set()

@app.callback(
    Output("splash-screen-container", "children"),
    Input("interval-component", "n_intervals"),
    State("splash-screen-container", "children"),
)
def update_splash_screen(n, children):
    global team_data
    new_team_data = read_json_data_from_api("http://127.0.0.1:5000/data1")  # read data from API
    with team_data_lock:
        if not new_team_data.equals(team_data):
            team_data = new_team_data
        dead_teams = team_data[team_data["liveMemberNum"] == 0]["teamName"]
    if len(dead_teams) > 0:
        for team in dead_teams:
            if team not in dead_teams_queue and team not in displayed_teams:
                dead_teams_queue.append(team)
        if len(dead_teams_queue) > 0:
            team = dead_teams_queue[0]
            start_time = getattr(app, f"{team}_start_time", None)  # Get start time from app object
            if children is None:
                # Set start time to current time when splash screen is first displayed
                start_time = time.time()
                setattr(app, f"{team}_start_time", start_time)  # Store start time in app object
                displayed_teams.add(team)  # Add team to set of displayed teams
                return generate_splash_screen(team, start_time)
            else:
                elapsed_time = time.time() - start_time
                if elapsed_time > 10:
                    dead_teams_queue.popleft()  # Remove first team from queue
                    if len(dead_teams_queue) > 0:
                        next_team = dead_teams_queue[0]
                        setattr(app, f"{next_team}_start_time", time.time())
                    return None
                else:
                    return generate_splash_screen(team, start_time)  # Update the splash screen with fade-out effect
    else:
        start_time = None
        if children is None:
            return None
        elapsed_time = time.time() - start_time
        if elapsed_time > 10:
            dead_teams_queue.popleft()  # Remove first team from queue
            if len(dead_teams_queue) > 0:
                next_team = dead_teams_queue[0]
                setattr(app, f"{next_team}_start_time", time.time())
            return None
        else:
            return children


if __name__ == "__main__":
    app.run_server(debug=False, port=8053, host="127.0.0.1")
