import datetime

from flask import Flask, send_file, request
from ImageToVideo import ImageToVideo, ImageClient, DatabaseConnection, clean_videos, clean_images
from bson.objectid import ObjectId
from datetime import datetime as dt
import json
import pprint
import requests

# cfg = None
app = Flask(__name__)

# URL de la raspi
images_url = "http://192.168.1.140/single"
# URL de la base de datos
# mongo_url = "mongodb+srv://cluster0.dmmkg.mongodb.net/" \
#             "?authSource=%24external&authMechanism=MONGODB-X509&retryWrites=true&w=majority"
mongo_url = "mongodb://localhost:27017"
files_base_url = "http://localhost:5000/files"

db = DatabaseConnection(conn_string=mongo_url, files_db='files', event_db='admin2')


@app.route("/event/timbre", methods=['POST'])
def event_timbre():
    print("Llego un request!")

    # Obtengo la IP de la request
    remote_ip = request.remote_addr
    # remote_port = request.
    # Llamo a la funcion para obtener el id de dispositivo
    # a partir de la IP
    db.connect()
    # Recibo un documento/dict
    document = db.get_device_by_ip(devices_collection='devices_device', ip=remote_ip)
    if document is None:
        return {'msg': 'Error con el dispositivo'}, 401

    # Obtener la foto
    port = document['port']
    r = None
    for picture in range(3):
        r = requests.get(url=f"http://{remote_ip}:{port}/single")
    # Guardar la foto
    if r is not None:
        file_data = db.insert_file(r.content)

    # Guardar evento con la referencia del archivo que se guardo
    event = {
        "id": str(file_data['id']),
        "date_time": dt.isoformat(dt.now()),
        "image": f"{files_base_url}/{file_data['filename']}",
        "device_id": document['id']
    }
    db.insert_event(event_collection='events_button', event_content=event)
    print(document['id'])
    return str(document['id'])


@app.route("/event/webbutton", methods=['POST'])
def event_webbutton():
    # Primero obtengo parametros de request
    host = request.json['host']
    port = request.json['port']
    user_id = request.json['user_id']
    device_id = request.json['device_id']

    print(f"{host} {port} {user_id} {device_id}")

    # Segundo obtener la foto
    for picture in range(5):
        r = requests.get(url=f"http://{host}:{port}/single")

    # Tercero guardar la foto
    db.connect()
    file_data = db.insert_file(r.content)

    # Cuarto guardar evento con la referencia del archivo que se guardo

    event = {
        "id": str(file_data['id']),
        "date_time": dt.isoformat(dt.now()),
        "user_id": user_id,
        "image": f"{files_base_url}/{file_data['filename']}",
        "device_id": device_id
    }
    db.insert_event(event_collection='events_webopendoor', event_content=event)

    # Quinto abro la puerta
    requests.get(url=f"http://{host}:{port}/cerradura")

    return {
        "msg": "Event registered"
    }, 200


@app.route("/record/<int:seconds>")
def video_recorder(seconds):
    filename = f'{datetime.datetime.now()}.avi'.replace(" ", "-")

    client = ImageClient(url=images_url)
    fps = client.get_images(tiempo=seconds)
    video_converter = ImageToVideo(video_path=filename)
    video_converter.video_from_images(fps=fps)
    clean_images()
    # db = DatabaseConnection(connection_string=mongo_url)
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
    # db = DatabaseConnection(connection_string=mongo_url)
    clean_videos()
    db.connect()
    db.load_from_db_grid(filename)
    return send_file(f"videos/{filename}", download_name=filename, as_attachment=True)


@app.route('/testupload/<string:event_type>/<string:filename>')
def get_event_picture(event_type, filename):
    # db = DatabaseConnection(conn_string=mongo_url)
    db.connect_local()
    db.save_event_file(filename, 'tesis')
    # data = db.load_event_file('2022-07-21-19:13:45.763157.avi,'
    #                           'tesis')
    # return data
    ret = {
        "id": str(filename),
        "filename": filename,
        "seconds": event_type,
        "msg": "A file was saved into db!"
    }
    return ret


@app.route('/files/<string:filename>')
def save_event_picture(filename):
    # db = DatabaseConnection(connection_string=mongo_url)
    db.connect_local()
    data = db.load_event_file(filename, 'files')
    # return send_file(data, mimetype='image/jpg')
    return data


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

    # db = DatabaseConnection(connection_string=mongo_url)
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
