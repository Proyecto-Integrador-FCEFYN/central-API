import datetime

from flask import Flask, send_file, request
from ImageToVideo import ImageToVideo, ImageClient, DatabaseConnection, clean_videos, clean_images
from bson.objectid import ObjectId
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
    clean_images()
    db = DatabaseConnection(connection_string=django_url)
    db.connect()
    file_id = db.save_to_db_grid(filename)
    ret = {
        "id": str(file_id),
        "filename": filename,
        "seconds": seconds,
        "msg": "A video was recorded!"
    }
    return ret


@app.route('/download/<string:filename>')
def download_file(filename):
    db = DatabaseConnection(connection_string=django_url)
    clean_videos()
    db.connect()
    db.load_from_db_grid(filename)
    return send_file(f"videos/{filename}", download_name=filename, as_attachment=True)


@app.route('/search')
def download_file_by_dict():
    my_dict = {}
    _id = request.args.get('id')
    if _id is not None:
        my_dict['_id'] = ObjectId(_id)
    _filename = request.args.get('filename')
    if _filename is not None:
        my_dict['filename'] = _filename
    _upload_date = request.args.get('uploadDate')
    if _upload_date is not None:
        my_dict['uploadDate'] = _upload_date
    _length = request.args.get('length')
    if _length is not None:
        my_dict['length'] = _length

    db = DatabaseConnection(connection_string=django_url)
    clean_videos()
    db.connect()

    document = db.load_from_db_dict(my_dict)
    if document == FileNotFoundError:
        return {
            'msg': "No file was found",
            'timestamp': datetime.datetime.now()
        }
    return send_file(f"videos/{document.filename}", download_name=document.filename, as_attachment=True)


@app.before_first_request
def load_json():
    with open("config.json") as json_data_file:
        data = json.load(json_data_file)
    pprint.pprint(data)
    return data
