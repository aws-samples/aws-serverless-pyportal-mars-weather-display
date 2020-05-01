# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import boto3
import botocore
import json
import PIL
from PIL import Image
from io import BytesIO
import requests
from random import randint
from datetime import date, timedelta

s3 = boto3.resource('s3')
session = boto3.session.Session()
region = session.region_name

bucket_name = os.environ.get('BUCKET')
nasa_api_key = os.environ.get('NASA_API_KEY')

key='mars_bg.bmp'
size_w = 320
size_h = 240

def getMarsInsightWeather():
    try:
        response = requests.get(
            'https://api.nasa.gov/insight_weather/',
            params={
                'api_key': nasa_api_key,
                'feedtype': 'json',
                'ver': 1.0
                }
        ).json()

        sol_keys = response['sol_keys']
        current_sol = sol_keys[len(sol_keys)-1]
        data = response[current_sol]

        return {
            'sol': current_sol,
            'av_at': data['AT']['av'],
            'av_HWS': data['HWS']['av'],
            'av_PRE': data['PRE']['av'],
            'Last_UTC': data['Last_UTC'],
            'First_UTC': data['First_UTC'],
            'season': data['Season']
        }
    except requests.RequestException as e:
        print(e)
        raise e

def fetchRoverImage():
    try:
        yesterday = date.today() - timedelta(days=1)
        yesterday = yesterday.strftime('20%y-%m-%d')

        response = requests.get(
            'https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos',
            params={
                'api_key': nasa_api_key,
                'page': 1,
                'earth_date': yesterday
                }
        ).json()
        photos = response['photos']
        max = len(photos) - 1
        url = photos[randint(0,max)]['img_src']
        return url
    except requests.RequestException as e:
        print(e)
        raise e

def fetchImageData(url):
    try:
        response = requests.get(url)
        return response.content
    except requests.RequestException as e:
        print(e)
        raise e

def resize_image(data):
    img = Image.open(BytesIO(data))
    img = img.resize((size_w, size_h))
    buffer = BytesIO()
    img.convert("P", colors=16).save(buffer, format="BMP")
    buffer.seek(0)

    obj = s3.Object(bucket_name=bucket_name, key=key)
    obj.put(Body=buffer, ContentType='image/bmp', ACL='public-read')

    return "https://{bucket}.s3.amazonaws.com/{key}".format(bucket=bucket_name, key=key)

def lambda_handler(event, context):
    url = fetchRoverImage()
    imgData = fetchImageData(url)
    image_s3_url = resize_image(imgData)
    weatherData = getMarsInsightWeather()

    return {
        "statusCode": 200,
        "body": json.dumps({
            "image_url": image_s3_url,
            "insight": weatherData
        })
    }
