import pandas as pd
import google.generativeai as genai


def get_predictions(csv_file1, csv_file2, year):
    genai.configure(api_key="AIzaSyCOYZ5rOlc1Sk4803cw_6jneb6SuvK7jSg")
    config = {
        "temperature": .2,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 500,
        "response_mime_type": "text/plain"
    }

    model = genai.GenerativeModel("gemini-1.5-flash")

    batters_data = pd.read_csv(csv_file1)
    pitchers_data = pd.read_csv(csv_file2)

    # transform csv data into text
    batters = batters_data.to_dict(orient='records')
    pitchers = pitchers_data.to_dict(orient='records')
    context = f"Predict the win/loss rate of a hypthetical baseball team in the season {year} consisting of the following players, based on their stats. Ignore the actual MLB team that each player plays for. Consider all players collectively, focusing on their batting averages, on-base percentages, slugging percentages for batters and any other statistics that will be relevant from the data, and other information you can gather about the players. Please only provide a singular, reasoned win percentage. The players are detailed here: Here is the data for batters:\n"

    # Add data to prompt for Gemini
    for row in batters:
        context += f"{row}\n"

    context += "Here is the data for pitchers:\n"

    for row in pitchers:
        context += f"{row}\n"

    # call to gemini
    response = model.generate_content(
        context, generation_config=config
    )

    # get response
    print("Response from Gemini API:")
    return response.text
