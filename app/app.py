import os
import tempfile
import uuid

from flask import Flask, send_file, request, make_response, Response
from werkzeug.middleware.proxy_fix import ProxyFix

from app.ImageToVideo import ImageToVideo, ImageClient, DatabaseConnection, clean_videos, clean_images
from bson.objectid import ObjectId
from datetime import datetime as dt, timedelta
import requests
import app.timbre as timbre

app = Flask(__name__)
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)
UPLOAD_FOLDER = 'certs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# URL de la base de datos
mongo_url = os.getenv('MONGO_URL', "mongodb://roberto:sanchez@192.168.24.120:27017/")
files_db = os.getenv('FILES_DB', "djongo")
event_db = os.getenv('EVENT_DB', "djongo")
tiempo_videos = os.getenv('TIEMPO_VIDEOS', 10)
cert_path = os.getenv('CERT_PATH', 'certs/cacert.pem')

db = DatabaseConnection(conn_string=mongo_url, files_db=files_db, event_db=event_db)


@app.route("/api/v1/event/rfid", methods=['POST'])
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
        is_staff = bool(user_document['is_staff'])

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
            }, 404

        # Una vez obtenida la zona horaria correspondiente al dia de la semana actual, se busca en la base
        # y se extraen los parametros para comparar
        timezone_doc = db.get_timezone_by_id('users_timezone', timezone_id)
        begin = timezone_doc['begin']
        end = timezone_doc['end']

    # Obtener dispositivo a partir de la ip de la request
    remote_ip = request.remote_addr
    device_document = db.get_device_by_ip(devices_collection='devices_device', ip=remote_ip)
    # Obtener certificado
    tmp_file = get_file_cert(remote_ip)
    if device_document is not None:
        # Obtener la foto
        port = device_document['port']
        device_id = device_document['id']
        usuario = device_document['usuario']
        password = device_document['password']

        r = None
        for picture in range(2):
            r = requests.get(url=f"https://{remote_ip}:{port}/single",
                             verify=tmp_file.name)

        # Guardar la foto
        if r is not None:
            file_data = db.insert_image(r.content)

    # Condiciones para el permiso:
    #   1. Que este en la franja horaria correcta
    #   2. Que el usuario este activo
    #   3. Que haya un usuario con el rfid que llego
    #   4. Que haya un dispositivo cargado con la ip de la request
    #   5. Que sea admin (is_staff)
    if user_document is not None and device_document is not None:
        event = {
            "id": str(file_data['id']),
            "date_time": dt.isoformat(dt.now()),
            "user_id": user_document['id'],
            "image": f"{file_data['filename']}",
            "device_id": device_document['id']
            }
        if is_staff:
            # Si es admin, no tiene begin ni end. Tiene permitido el acceso en todo horario.
            print('Admin detectado, permiso otorgado')
            db.insert_event(event_collection='events_permittedaccess', event_content=event)
            # Abro la puerta
            requests.get(url=f"https://{usuario}:{password}@{remote_ip}:{device_document['port']}/cerradura",
                         verify=tmp_file.name)
        elif begin <= end:
            if (begin < current_time < end) \
                    and is_active:
                print('Permiso otorgado')

                db.insert_event(event_collection='events_permittedaccess', event_content=event)
                # Abro la puerta
                requests.get(url=f"https://{usuario}:{password}@{remote_ip}:{device_document['port']}/cerradura",
                             verify=tmp_file.name)
        elif begin > end:
            if current_time < begin:
                current_time = current_time + timedelta(days=1)
            if (begin < current_time < end + timedelta(days=1)) \
                    and is_active:
                # Permiso otorgado
                db.insert_event(event_collection='events_permittedaccess', event_content=event)
                # Abro la puerta
                requests.get(url=f"https://{usuario}:{password}@{remote_ip}:{device_document['port']}/cerradura",
                             verify=tmp_file.name)
    else:
        print('Permiso denegado')
        event = {
            "id": str(file_data['id']),
            "date_time": dt.isoformat(dt.now()),
            "image": f"{file_data['filename']}",
            "device_id": device_id
            }
        db.insert_event(event_collection='events_deniedaccess', event_content=event)
    tmp_file.close()
    ret = {
        "msg": "Se genero un evento!"
    }
    return ret


@app.route("/api/v1/event/movimiento", methods=['POST'])
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
        return ret, 404

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
        else:
            ret = {'msg': 'Fuera de la franja horaria de deteccion de movimiento'}
            print(ret)
            return ret, 404
    elif begin > end:
        if current_time < begin:
            current_time = current_time + timedelta(days=1)
        if begin < current_time < end + timedelta(days=1):
            print(ret)
        else:
            ret = {'msg': 'Fuera de la franja horaria de deteccion de movimiento'}
            print(ret)
            return ret, 404
        # print(f"{begin} {current_time} {end} ")
    else:
        ret = {'msg': 'Fuera de la franja horaria de deteccion de movimiento'}
        print(ret)
        return ret, 404

    # Obtener el video
    port = document['port']

    # Este nombre es el que tendra el video final en el filesystem
    # filename = f'{str(uuid.uuid4())}.mp4'
    filename = f'{str(uuid.uuid4())}.gif'
    # Nombre de carpeta unica de cada solicitud
    folder_name = str(uuid.uuid4())
    # Obtener certificado
    tmp_file = get_file_cert(remote_ip)
    # Obtener las imagenes y traerlos al filesystem local
    client = ImageClient(url=f"https://{remote_ip}:{port}/single", folder_name=folder_name)
    fps = client.get_images(tiempo=tiempo_videos, verify_path=tmp_file.name)
    tmp_file.close()
    
    # Convertir las imagenes en video
    video_converter = ImageToVideo(filename=filename, folder_name=folder_name)
    # if not video_converter.video_from_images2(fps=fps):
    #     ret = {'msg': 'Error con la generacion del video'}
    #     print(ret)
    #     clean_images(folder_name=folder_name)
    #     clean_videos()
    #     return ret, 500
    video_converter.make_animation(fps=fps)
    
    # Guardar el video
    file_data = db.insert_video(filename=filename)
    clean_images(folder_name=folder_name)
    clean_videos()
    if file_data is None:
        return {'msg': 'Error en el guardado del video'}, 500

    # Guardar evento con la referencia del archivo que se guardo
    event = {
        "id": str(file_data['id']),
        "date_time": dt.isoformat(dt.now()),
        "image": f"{file_data['filename']}",
        "device_id": document['id']
    }
    ret = db.insert_event(event_collection='events_movement', event_content=event)
    # print(ret)
    return {'msg': 'Evento guardado satisfactoriamente'}, 200


@app.route("/api/v1/event/timbre", methods=['POST'])
def event_timbre():
    print("Llego un request!")
    timbre.sonar()

    # Obtengo la IP de la request
    remote_ip = request.remote_addr
    # remote_port = request.
    # Llamo a la funcion para obtener el id de dispositivo
    # a partir de la IP
    db.connect()
    # Recibo un documento/dict
    document = db.get_device_by_ip(devices_collection='devices_device', ip=remote_ip)
    if document is None:
        return {'msg': 'Error con el dispositivo'}, 404

    # Obtener archivo certificado
    tmp_file = get_file_cert(ip_address=remote_ip)
    # Obtener la foto
    port = document['port']
    r = None
    for picture in range(2):
        r = requests.get(url=f"https://{remote_ip}:{port}/single",
                         verify=tmp_file.name)
    tmp_file.close()

    # Guardar la foto
    if r is not None:
        file_data = db.insert_image(r.content)

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


@app.route("/api/v1/event/webbutton", methods=['POST'])
def event_webbutton():
    print("Evento webbutton!")
    # Primero obtengo parametros de request
    host = request.json['host']
    port = request.json['port']
    user_id = request.json['user_id']
    device_id = request.json['device_id']
    usuario_esp = request.json['usuario']
    password_esp = request.json['password']

    db.connect()
    print(f"{host} {port} {user_id} {device_id}")
    # Obtener certificado
    tmp_file = get_file_cert(ip_address=host)
    # Segundo obtener la foto
    for picture in range(2):
        r = requests.get(url=f"https://{host}:{port}/single",
                         verify=tmp_file.name)

    # Tercero guardar la foto
    file_data = db.insert_image(r.content)

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
    requests.get(url=f"https://{usuario_esp}:{password_esp}@{host}:{port}/cerradura",
                 verify=tmp_file.name)
    tmp_file.close()
    return {
        "msg": "Event registered"
    }, 200



@app.route('/api/v1/files/<string:filename>')
def save_event_picture(filename):
    db.connect()
    data = db.load_event_file(filename, files_db)
    response = make_response(data)
    if str(filename).endswith('.jpg'):
        response.headers.set('Content-Type', 'image/jpeg')
    elif str(filename).endswith('.mp4'):
        response.headers.set('Content-Type', 'video/mp4')
    elif str(filename).endswith('.gif'):
        response.headers.set('Content-Type', 'image/gif')
    return response

@app.route('/api/v1/rfid', methods=['POST'])
def get_current_rfid():
    print("Llego una requestde rfid!")
    # Obtengo la IP
    host = request.json['host']
    port = request.json['port']
    usuario_esp = request.json['usuario']
    password_esp = request.json['password']
    # Llamo a la funcion para obtener el id de dispositivo
    # a partir de la IP
    db.connect()
    tmp_file = get_file_cert(ip_address=host)
    # Recibo un documento/dict
    document = db.get_device_by_ip(devices_collection='devices_device', ip=host)
    if document is None:
        return {'msg': 'Error con el dispositivo'}, 500
   # Quinto abro la puerta
    r =requests.get(url=f"https://{usuario_esp}:{password_esp}@{host}:{port}/register_rfid",
                 verify=tmp_file.name)
    tmp_file.close()
    return {
        "rfid": str(r.text)
    }, 200


@app.route('/api/v1/search')
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

    db.connect()
    document = db.load_from_db_dict(my_dict)
    if document == FileNotFoundError:
        return {
            'msg': "No file was found",
            'timestamp': dt.now()
        }

    resp = make_response(document)
    resp.headers['Content-Type'] = 'text/plain;charset=UTF-8'
    resp.headers['Content-Disposition'] = f'attachment;filename={_filename}'
    return resp


def gen(host, port, duracion):
    # Obtener certificado
    db.connect()
    tmp_file = get_file_cert(host)
    duracion = dt.now() + timedelta(seconds=int(duracion))
    # mientras el tiempo actual sea menor que el parametro
    s = requests.Session()
    while dt.now() < duracion:
        r = s.get(url=f"https://{host}:{port}/single", verify=tmp_file.name)
        frame = r.content
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    tmp_file.close()
    s.close()


@app.route('/api/v1/streaming', methods=['GET'])
def pasamano():
    duracion = request.args.get('duracion')
    host = request.args.get('host')
    port = request.args.get('port')

    if port is None or host is None or duracion is None:
        return {
            'msg': 'Error en los parametros',
            'params': [duracion, host, port]
        }, 400

    return Response(gen(host=host, port=port, duracion=duracion),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/v1/test')
def test():
    return {
        'msg': 'This a is great test!'
    }



def get_file_cert(ip_address: str):
    tmp = tempfile.NamedTemporaryFile(mode='w')
    doc = db.get_cert_content(collection='devices_device', device_ip=ip_address)
    cert_str = doc['cert']
    tmp.write(cert_str)
    tmp.seek(0)
    return tmp
