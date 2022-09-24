import datetime
import os

from flask import Flask, send_file, request
from ImageToVideo import ImageToVideo, ImageClient, DatabaseConnection, clean_videos, clean_images
from bson.objectid import ObjectId
from datetime import datetime as dt
import json
import pprint
import requests

# cfg = None
app = Flask(__name__)


# URL de la base de datos
# mongo_url = "mongodb://localhost:27017"
# mongo_url = "mongodb://djongo:dj0ng0@24.232.132.26:27015/?authMechanism=DEFAULT&authSource=djongo"
mongo_url = os.getenv('MONGO_URL', "mongodb://roberto:sanchez@150.136.250.71:27017/")
# files_base_url = "http://localhost:5000/files"
files_db = os.getenv('FILES_DB', "djongo")
event_db = os.getenv('EVENT_DB', "djongo")

db = DatabaseConnection(conn_string=mongo_url, files_db=files_db, event_db=event_db)


@app.route("/event/rfid", methods=['POST'])
def event_rfid():
    print("Llego un request de RFID")
    now = dt.now()
    db.connect()

    # Transformar el dato binario que viene de la request
    rfid = request.get_data().replace(b'\x02', b'').replace(b'\x03', b'').decode('ascii')

    # Extraer la hora actual y formatearla como viene begin y end con fecha de 1900-01-01.
    # Se puede comparar las horas con < y > si la fecha es la misma.
    current_time = dt.strptime(f'1900-01-01 {now.strftime("%H:%M:%S")}', "%Y-%j-%d %H:%M:%S")

    # Conseguir ID usuario a partir de RFID
    print(f"Recibi en la request en codigo {rfid}")
    user_document = db.get_user_by_rfid(devices_collection='users_user', rfid=rfid)

    if user_document is not None:
        is_active = bool(user_document['is_active'])

        # Calcular el dia de la semana y averiguar contra que ID hay que comparar
        weekday = now.isoweekday()
        if weekday == 1:
            timezone_id = user_document['monday_id']
        elif weekday == 2:
            timezone_id = user_document['tuesday_id']
        elif weekday == 3:
            timezone_id = user_document['wednesday_id']
        elif weekday == 4:
            timezone_id = user_document['thursday_id']
        elif weekday == 5:
            timezone_id = user_document['friday_id']
        elif weekday == 6:
            timezone_id = user_document['saturday_id']
        elif weekday == 7:
            timezone_id = user_document['sunday_id']
        else:
            return {
                "msg": f"Error con la weekday y timezone {weekday}"
            }, 401

        # Una vez obtenida la zona horaria correspondiente al dia de la semana actual, se busca en la base
        # y se extraen los parametros para comparar
        timezone_doc = db.get_timezone_by_id('users_timezone', timezone_id)
        begin = timezone_doc['begin']
        end = timezone_doc['end']

    # Obtener dispositivo a partir de la ip de la request
    remote_ip = request.remote_addr
    device_document = db.get_device_by_ip(devices_collection='devices_device', ip=remote_ip)
    if device_document is not None:
        # Obtener la foto
        port = device_document['port']
        device_id = device_document['id']
        r = None
        for picture in range(3):
            r = requests.get(url=f"http://{remote_ip}:{port}/single")
        # Guardar la foto
        if r is not None:
            file_data = db.insert_file(r.content)

    # Condiciones para el permiso:
    #   1. Que este en la franja horaria correcta
    #   2. Que el usuario este activo
    #   3. Que haya un usuario con el rfid que llego
    #   4. Que haya un dispositivo cargado con la ip de la request
    if user_document is not None and device_document is not None:
        event = {
            "id": str(file_data['id']),
            "date_time": dt.isoformat(dt.now()),
            "user_id": user_document['id'],
            "image": f"{file_data['filename']}",
            "device_id": device_document['id']
            }
        if begin <= end:
            if (begin < current_time < end or timezone_id == 1) \
                    and bool(user_document['is_active']):
                print('Permiso otorgado')

                db.insert_event(event_collection='events_permittedaccess', event_content=event)
                # Abro la puerta
                requests.get(url=f"http://{remote_ip}:{device_document['port']}/cerradura")
        elif begin > end:
            if current_time < begin:
                current_time = current_time + datetime.timedelta(days=1)
            if (begin < current_time < end + datetime.timedelta(days=1) or timezone_id == 1) \
                    and bool(user_document['is_active']):
                # Permiso otorgado
                db.insert_event(event_collection='events_permittedaccess', event_content=event)
                # Abro la puerta
                requests.get(url=f"http://{remote_ip}:{device_document['port']}/cerradura")

    else:
        print('Permiso denegado')
        event = {
            "id": str(file_data['id']),
            "date_time": dt.isoformat(dt.now()),
            "image": f"{file_data['filename']}",
            "device_id": device_id
            }
        db.insert_event(event_collection='events_deniedaccess', event_content=event)

    ret = {
        "msg": "Se genero un evento!"
    }
    return ret


@app.route("/event/movimiento", methods=['POST'])
def event_movimiento():
    print("Llego un request del sensor de movimiento!")


    # Obtengo la IP de la request
    remote_ip = request.remote_addr

    # Llamo a la funcion para obtener el id de dispositivo
    # a partir de la IP
    db.connect()
    # Recibo un documento/dict
    document = db.get_device_by_ip(devices_collection='devices_device', ip=remote_ip)
    if document is None:
        ret = {'msg': 'Error con el dispositivo'}
        print(ret)
        return ret, 401

    # Preguntar por el timezone del detector de movimiento

    # Extraer la hora actual y formatearla como viene begin y end con fecha de 1900-01-01.
    # Se puede comparar las horas con < y > si la fecha es la misma.
    now = dt.now()
    current_time = dt.strptime(f'1900-01-01 {now.strftime("%H:%M:%S")}', "%Y-%j-%d %H:%M:%S")
    # Una vez obtenida la zona horaria correspondiente al dia de la semana actual, se busca en la base
    # y se extraen los parametros para comparar
    timezone_doc = db.get_timezone_by_id('events_movementtimezone', 1)  # tiene ID siempre 1
    begin = timezone_doc['begin']
    end = timezone_doc['end']

    # Pura magia:
    # La zona horaria puede empezar un dia y terminar en otro, por ejemplo 22 a 8.
    # Entonces hay dos casos, si esta en el mismo dia o no.
    # Si no esta en el mismo dia, hay que ver si la hora actual esta en el dia de
    # begin, si no esta se le suma un dia. Y a end se le suma un dia siempre.
    ret = {'msg': 'Dentro de la zona horaria de la deteccion de movimiento'}
    if begin < end:
        if begin < current_time < end:
            print(ret)
    elif begin > end:
        if current_time < begin:
            current_time = current_time + datetime.timedelta(days=1)
        if begin < current_time < end + datetime.timedelta(days=1):
            print(ret)
        print(f"{begin} {current_time} {end} ")
    else:
        ret = {'msg': 'Fuera de la franja horaria de deteccion de movimiento'}
        print(ret)
        return ret, 401

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
        "image": f"{file_data['filename']}",
        "device_id": document['id']
    }
    db.insert_event(event_collection='events_movement', event_content=event)
    print(document['id'])
    return str(document['id'])


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
        "image": f"{file_data['filename']}",
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
        "image": f"{file_data['filename']}",
        "device_id": device_id
    }
    db.insert_event(event_collection='events_webopendoor', event_content=event)

    # Quinto abro la puerta
    requests.get(url=f"http://{host}:{port}/cerradura")

    return {
        "msg": "Event registered"
    }, 200


@app.route("/record/")
def video_recorder():

    db.connect()
    seconds = request.args.get('seconds', default=10, type=int)
    device_url = request.args.get('url', type=str)
    filename = f'{dt.isoformat(dt.now())}.avi'

    client = ImageClient(url=f"{device_url}/single")
    fps = client.get_images(tiempo=seconds)
    video_converter = ImageToVideo(video_path=filename)
    video_converter.video_from_images(fps=fps)
    clean_images()
    # db = DatabaseConnection(connection_string=mongo_url)
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
    # db.connect_local()
    db.connect()
    data = db.load_event_file(filename, files_db)
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
