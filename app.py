import datetime

from flask import Flask, request, send_file
from ImageToVideo import ImageToVideo, ImageClient, DatabaseConnection
import json
import pprint

# cfg = None
app = Flask(__name__)

images_url = "http://192.168.1.140/single"
django_url = "mongodb+srv://cluster0.dmmkg.mongodb.net/" \
      "?authSource=%24external&authMechanism=MONGODB-X509&retryWrites=true&w=majority"


@app.route("/record/<int:seconds>")
def video_recorder(seconds):

    filename = f'{datetime.datetime.now()}.avi'.replace(" ", "-")

    client = ImageClient(url=images_url)
    fps = client.get_images(tiempo=seconds)
    video_converter = ImageToVideo(video_path=filename)
    video_converter.video_from_images(fps=fps)
    client.clean_images()
    db = DatabaseConnection(connection_string=django_url)
    db.connect()
    file_id = db.save_to_db_grid(filename)
    return f"A video with id: {file_id} of {seconds} seconds has been recorded!"


@app.route('/download/<string:filename>')
def download_file(filename):
    db = DatabaseConnection(connection_string=django_url)
    db.clean_videos()
    db.connect()
    db.load_from_db_grid(filename)
    return send_file(f"videos/{filename}", download_name=filename, as_attachment=True)


@app.before_first_request
def load_json():
    with open("config.json") as json_data_file:
        data = json.load(json_data_file)
    pprint.pprint(data)
    return data
