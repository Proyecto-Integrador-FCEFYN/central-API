import datetime
import uuid
import os
import imageio.v2 as imageio

import requests as r
import time
from pymongo import MongoClient, DESCENDING
from bson.binary import Binary
import gridfs
from datetime import datetime as dt


class ImageToVideo:

    def __init__(self, filename, folder_name):
        self.filename = filename
        self.folder_name = folder_name

    def video_from_images2(self, fps):
        if not os.path.exists('videos'):
            os.makedirs('videos')
        if not os.path.exists(self.folder_name):
            return {'msg': 'No se pudo crear el directorio para la conversion'}
        images = [img for img in os.listdir(self.folder_name) if img.endswith(".jpg")]
        images.sort()
        # -crf is Constant Rate Factor
        # -pix_fmt yuv420p is for Apple Quicktime support
        os.system(f"ffmpeg -an -i {self.folder_name}/%d.jpg -vcodec libx264 -pix_fmt yuv420p -profile:v baseline -level 3 -crf {fps/2} -y videos/{self.filename}")
        for wait in range(10):
            if not os.path.exists(f"videos/{self.filename}"):
                print("Esperando que se genere el video...")
                time.sleep(1)
            else: 
                print(f"Converti el archivo {self.filename}!")
                return True
        return False
    
    def make_animation(self, fps):
        png_dir = self.folder_name
        images = []
        for file_name in sorted(os.listdir(png_dir)):
            if file_name.endswith('.jpg'):
                file_path = os.path.join(png_dir, file_name)
                images.append(imageio.imread(file_path))

        # Make it pause at the end so that the viewers can ponder
        for _ in range(10):
            images.append(imageio.imread(file_path))

        imageio.mimsave(f"videos/{self.filename}", images, fps=fps)


def clean_images(folder_name):
    images = [img for img in os.listdir(folder_name)]
    for path in images:
        os.remove(f'{folder_name}/{path}')
    os.removedirs(folder_name)


class ImageClient:

    def __init__(self, url, folder_name):
        self.url = url
        self.folder_name = folder_name

    def get_images(self, tiempo, verify_path):
        images_array = []
        cantidad = 0  # cantidad de frames
        timestamp_salida = time.time() + tiempo
        s = r.Session()
        while time.time() < timestamp_salida:
            response = s.get(url=self.url, stream=True,
                             verify=verify_path)
            images_array.append(response.content)
        s.close()
        os.makedirs(self.folder_name, exist_ok=True)
        for image in images_array:
            f = open(f'{self.folder_name}/{cantidad}.jpg', "wb")
            cantidad += 1
            f.write(image)
            f.close()
        print(f'cant frames= {cantidad}, seg={tiempo}, fps={cantidad / tiempo}')
        return cantidad / tiempo


def clean_videos():
    images = [img for img in os.listdir('videos')]
    for path in images:
        os.remove(f'videos/{path}')


class DatabaseConnection:
    client = None

    def __init__(self, conn_string, files_db, event_db):
        self.client = None
        self.conn_string = conn_string
        self.files_db = files_db
        self.event_db = event_db

    def connect(self):
        # if 'localhost' in self.conn_string:
        self.client = MongoClient(self.conn_string)
        # else:
        #     self.client = MongoClient(self.conn_string,
        #                               tls=True,
        #                               tlsCertificateKeyFile='config/agustin2022.pem',
        #                               server_api=ServerApi('1'))

    def close_connection(self):
        self.client.close()
        print("Se ha cerrado la conexion a la DB!")

    def connect_local(self):
        self.client = MongoClient(self.conn_string)

    def insert_video(self, filename):
        db = self.client[self.files_db]
        fs = gridfs.GridFS(db)
        with open(f'videos/{filename}', "rb") as f:
            encoded = Binary(f.read())
        file_id = fs.put(data=encoded, filename=filename)
        print(f'the file with id: {file_id} has been saved')
        ret = {
            "id": file_id,
            "filename": f"{filename}",
            "uuid": filename,
            "msg": "The file has been saved!"
        }
        return ret

    def load_from_db_grid(self, filename):
        db = self.client['tesis']
        # collection = db['files']
        fs = gridfs.GridFS(db)
        document = fs.find_one({
            "filename": filename
        })
        print(document)
        binary_data = document.read()
        with open(f'videos/{filename}', "wb") as f:
            data = Binary(binary_data)
            f.write(data)
        print(f" El archivo {document.filename} ha sido guardado")

    def load_from_db_dict(self, search_dict):
        db = self.client[self.files_db]
        # collection = db['files']
        fs = gridfs.GridFS(db)
        document = fs.find_one(search_dict, sort=[('uploadDate', DESCENDING)])
        if document is None:
            return FileNotFoundError
        print(f'Se encontro un archivo con nombre: {document.filename}')
        binary_data = document.read()
        return binary_data

    def load_event_file(self, filename, database='files'):
        db = self.client[database]
        fs = gridfs.GridFS(db)
        document = fs.find_one({
            "filename": filename
        })
        # print(document)
        binary_data = document.read()
        print(f" El archivo {document.filename} ha sido encontrado")
        return Binary(binary_data)

    # Se pasa el payload del archivo, que seria la foto
    # que vino por mqtt.
    # Devuelve el nombre del archivo asignado.
    def insert_image(self, payload):
        filename = str(uuid.uuid4())
        db = self.client[self.files_db]
        fs = gridfs.GridFS(db)
        encoded = Binary(payload)
        file_id = fs.put(data=encoded, filename=f"{filename}.jpg", uuid=filename)
        ret = {
            "id": file_id,
            "filename": f"{filename}.jpg",
            "uuid": filename,
            "msg": "The file has been saved!"
        }
        return ret

    def insert_file(self, payload, my_filename):
        # filename = str(uuid.uuid4())
        db = self.client[self.files_db]
        fs = gridfs.GridFS(db)
        encoded = Binary(payload)
        file_id = fs.put(data=encoded, filename=my_filename, uuid=my_filename)
        ret = {
            "id": file_id,
            "filename": my_filename,
            "uuid": my_filename,
            "msg": "The file has been saved!"
        }
        return ret

    def insert_event(self, event_collection, event_content):
        db = self.client[self.event_db]
        collection = db[event_collection]
        result = collection.insert_one(event_content)
        ret = {
            "inserted_id": result.inserted_id,
            "msg": "The record has been saved!"
        }
        return ret

    def get_device_by_ip(self, devices_collection, ip):
        db = self.client[self.event_db]
        collection = db[devices_collection]
        document = collection.find_one(
            {
                "ip_address": ip
            }
        )
        return document

    def get_user_by_rfid(self, devices_collection, rfid):
        db = self.client[self.event_db]
        collection = db[devices_collection]
        document = collection.find_one(
            {
                "code": rfid
            }
        )
        return document

    def get_timezone_by_id(self, tz_collection, tz_id):
        db = self.client[self.event_db]
        collection = db[tz_collection]
        document = collection.find_one(
            {
                "id": tz_id
            }
        )
        return document


    def get_cert_content(self, collection, device_ip):
        db = self.client[self.event_db]
        collection = db[collection]
        document = collection.find_one({"ip_address": device_ip})
        if document is not None:
            return document
        else:
            return {'msg': 'Not found'}

    def get_events_duration(self):
        # Realizar la consulta a la base de datos para obtener la duración de los eventos
        db = self.client[self.event_db]
        collection = db['events_eventsduration']
        duracion_eventos = collection.find_one({"id": 1})
        if duracion_eventos:
            return {
                'year': duracion_eventos.get('year', 0),
                'month': duracion_eventos.get('month', 0)
            }
        else:
            # En caso de que no se encuentre ninguna duración de eventos en la base de datos,
            # se devuelven en 0, que hace que no se eliminen los datos.
            return {
                'year': 0,
                'month': 0
            }


    def borrar_eventos_antiguos(self, fecha_limite):
        # Obtener la colección de eventos
        db = self.client[self.event_db]

        # Obtener la lista de nombres de todas las colecciones en la base de datos
        all_collections = db.list_collection_names()

        # Eliminar "events_eventduration" y "events_movementtimezone" de la lista
        if "events_eventsduration" in all_collections:
            all_collections.remove("events_eventsduration")
        if "events_movementtimezone" in all_collections:
            all_collections.remove("events_movementtimezone")

        # Filtrar las colecciones que empiecen con "events_"
        eventos_collections = [collection for collection in all_collections if collection.startswith("events_")]

        # Iterar sobre las colecciones de eventos y eliminar eventos antiguos
        for collection_name in eventos_collections:
            eventos_collection = db[collection_name]

            # Realizar la consulta para encontrar y eliminar los eventos antiguos
            resultado = eventos_collection.delete_many({"date_time": { "$lt": fecha_limite }})
            if resultado.deleted_count:
                print(f"Cantidad de eventos eliminados en {collection_name}: {resultado.deleted_count}")
