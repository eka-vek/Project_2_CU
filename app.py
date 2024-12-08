import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import math
from collections import OrderedDict



app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['JSON_AS_ASCII'] = False

api_key = "YdasPwoz3MNx0XIypfsL1Gq5KLU2sFqe"
url  = "http://dataservice.accuweather.com/"

@app.route('/')
def hello_world():
    return render_template('hello.html')
# получение ключа для координат
def get_location_key(location):
    location_url = f"{url}locations/v1/cities/search?apikey={api_key}&q={location}"
    try:
        response = requests.get(location_url)
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0]['Key']
        else:
            return None  #рез-ов не найдено
    except requests.exceptions.RequestException as e:
        return None


# Получение данных о погоде с сайта
def get_weather_data(location_key):
    weather_url = f"{url}currentconditions/v1/{location_key}?apikey={api_key}&details=true"
    try:
        response = requests.get(weather_url)
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0]
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None

#функция для определения качества погоды
def check_bad_weather(temperature_c, wind_speed, rain_probability, humidity):
#усложним логику оценки, добавим каждому показателю коэффициент важности,
 #т.к. например температура зачастую важнее учитывается, чем влажность'''
    temp_weight = 0.4  # вклад температуры
    wind_weight = 0.3  # вклад ветра
    rain_weight = 0.6  # вклад возможности осадков


    # Будем оценивать погоду по общему показателю, чем он выше, тем погода хуже
    temp_score = 0
    if temperature_c < 5:
        temp_score = (5 - temperature_c) * temp_weight  #холодно
    elif temperature_c > 25:
        temp_score = (temperature_c - 25) * temp_weight #слишком жарко
    wind_score = min(wind_speed / 50, 1) * wind_weight #приводим к нужной СС
    rain_score = min(rain_probability / 70, 1) * rain_weight #-//-
    humidity_score = min(humidity / 90,1)*0.2 #-//-

    total_score = temp_score + wind_score + rain_score + humidity_score

    # Set thresholds for weather conditions (adjust as needed)
    if total_score > 0.9:
        return "Погода отвратная, лучше останьтесь дома и приготовьте что-нибудь вкусное!"
    elif total_score > 0.4:
        return "Погода так себе, лучше выбрать автобусную экскурсию и взять дождевик."
    else:
        return "Отличная погода! Идеальна для пешей экскурсии или просто прогулки."
#получение данных с помощью API-запроса методом GET
@app.route('/weather', methods=['GET'])
def get_weather():
    #обработка ошибок
    location = request.args.get('location')
    if not location:
        return render_template('error.html', message="Ведите хотя бы одну точку маршрута."), 400

    location_key = get_location_key(location)
    if location_key is None:
        return render_template('error.html', message="Ой, похоже такого города не существует, введите другой"), 404

    weather_data = get_weather_data(location_key)
    if weather_data is None:
        return render_template('error.html', message="Упссс..У нас нет информации о погоде в этом районе "), 500


    try:
        temperature_c = weather_data['Temperature']['Metric']['Value']
        humidity = weather_data['RelativeHumidity']
        wind_speed = weather_data['Wind']['Speed']['Metric']['Value']
        rain_probability = weather_data.get('PrecipitationSummary', {}).get('Probability', 0)

        weather_advice = check_bad_weather(temperature_c, wind_speed, rain_probability)

        result = OrderedDict([
            ('temperature_c', temperature_c),
            ('humidity', humidity),
            ('wind_speed', wind_speed),
            ('rain_probability', rain_probability),
            ('location', location),
            ('z_weather_advice', weather_advice)
        ])

        return jsonify(result), 200, {'Content-Type': 'application/json; charset=utf-8'}

    except (KeyError, TypeError) as e:
        return render_template('error.html', message="Ох, ошибка обработки данных, вернитесь к запросу чуть позже, когда мы всё поправим"), 500


@app.route('/weather_check', methods=['POST'])
def weather_check():
    locations_str = request.form.get('locations')
    if not locations_str:
        return render_template('error.html', message="Ведите хотя бы одну точку маршрута."), 400

    locations = [loc.strip() for loc in locations_str.splitlines() if loc.strip()]
    if not locations:
        return render_template('error.html', message="Такой точки нет в базе данных, введите другую"), 400

    weather_data_all = []
    for location in locations:
        try:
            location_key = get_location_key(location)
            if location_key is None:
                return render_template('error.html', message="Нет сети, включите интернет. Если интернет включен, значит введённого места не существует, попробуйте ещё раз"), 404

            weather_data = get_weather_data(location_key)
            if weather_data is None:
                return render_template('error.html', message="Ой, нет данных о погоде для этого местоположения"), 500

            temperature_c = weather_data['Temperature']['Metric']['Value']
            humidity = weather_data['RelativeHumidity']
            wind_speed = weather_data['Wind']['Speed']['Metric']['Value']
            rain_probability = weather_data.get('PrecipitationSummary', {}).get('Probability', 0)

            weather_advice = check_bad_weather(temperature_c, wind_speed, rain_probability, humidity)

            weather_data_all.append({
                'location': location,
                'weather_advice': weather_advice,
                'temperature_c': temperature_c,
                'humidity': humidity,
                'wind_speed': wind_speed,
                'rain_probability': rain_probability,
            })

        except (KeyError, TypeError, requests.exceptions.RequestException) as e:
            return render_template('error.html', message="Ой, ошибка в обработке данных, пожалуйста, попробуйте ещё раз"), 500

    return render_template('answer.html', weather_data=weather_data_all)

if __name__ == '__main__':
    app.run(debug=True)