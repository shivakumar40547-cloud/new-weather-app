
from flask import Flask, render_template, request, jsonify
import requests
from datetime import date

app = Flask(__name__)

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather_description(code):
    descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Rime fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Heavy drizzle",
        61: "Light rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Light snowfall",
        73: "Snowfall",
        75: "Heavy snowfall",
        80: "Rain showers",
        81: "Rain showers",
        82: "Heavy rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with hail"
    }
    return descriptions.get(code, "Weather unavailable")


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/api/weather")
def weather():
    city = request.args.get("city", "Hyderabad").strip()

    if not city:
        return jsonify({"error": "Please enter a city name."}), 400

    try:
        # Step 1: Find the city's latitude and longitude
        geo_response = requests.get(
            GEO_URL,
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json"
            },
            timeout=15
        )
        geo_response.raise_for_status()

        locations = geo_response.json().get("results", [])

        if not locations:
            return jsonify({"error": "City not found. Try another name."}), 404

        location = locations[0]
        latitude = location["latitude"]
        longitude = location["longitude"]

        # Step 2: Fetch current weather and a 5-day forecast
        weather_response = requests.get(
            WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,relative_humidity_2m,"
                    "apparent_temperature,is_day,weather_code,"
                    "wind_speed_10m,surface_pressure"
                ),
                "daily": (
                    "weather_code,temperature_2m_max,"
                    "temperature_2m_min"
                ),
                "hourly": "uv_index",
                "forecast_days": 5,
                "timezone": "auto"
            },
            timeout=15
        )
        weather_response.raise_for_status()

        result = weather_response.json()
        current = result["current"]
        daily = result["daily"]
        hourly = result["hourly"]

        # Find the UV index for the current local hour
        current_time = current["time"]
        uv_values = hourly["uv_index"]
        hourly_times = hourly["time"]

        try:
            uv = uv_values[hourly_times.index(current_time)]
        except (ValueError, IndexError):
            uv = 0

        # Step 3: Prepare forecast data for the frontend
        forecast = []

        for i, forecast_date in enumerate(daily["time"]):
            forecast.append({
                "day": date.fromisoformat(forecast_date).strftime("%a"),
                "code": daily["weather_code"][i],
                "condition": get_weather_description(
                    daily["weather_code"][i]
                ),
                "max": daily["temperature_2m_max"][i],
                "min": daily["temperature_2m_min"][i]
            })

        # Step 4: Return JSON to the HTML page
        return jsonify({
            "city": location["name"],
            "temperature": current["temperature_2m"],
            "feels_like": current["apparent_temperature"],
            "condition": get_weather_description(
                current["weather_code"]
            ),
            "code": current["weather_code"],
            "is_day": current["is_day"] == 1,
            "humidity": current["relative_humidity_2m"],
            "wind": current["wind_speed_10m"],
            "pressure": current["surface_pressure"],
            "uv": uv,
            "forecast": forecast
        })

    except requests.RequestException:
        return jsonify({
            "error": "Weather service unavailable. Please try again."
        }), 502

    except (KeyError, TypeError, IndexError):
        return jsonify({
            "error": "Unexpected weather data. Please try again."
        }), 502


if __name__ == "__main__":
    app.run(debug=True)
