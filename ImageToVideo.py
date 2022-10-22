import datetime
import uuid
import os

import requests
import requests as r
import time
from pymongo import MongoClient, DESCENDING
from bson.binary import Binary
import gridfs
from datetime import datetime as dt


class ImageToVideo:

    def __init__(self, filename):
        self.filename = filename

    def video_from_images2(self, fps):
        image_folder = 'images'
        images = [img for img in os.listdir(image_folder) if img.endswith(".jpg")]
        images.sort()
        # os.system(f"ffmpeg -r {fps} -i images/%d.jpg -vcodec mpeg4 -y videos/{self.filename}")
        os.system(f"ffmpeg -an -i images/%d.jpg -vcodec libx264 -pix_fmt yuv420p -profile:v baseline -level 3 -r {fps/1.4} -y videos/{self.filename}")
        print(f"Converti el archivo {self.filename}!")


def clean_images():
    images = [img for img in os.listdir('images')]
    for path in images:
        os.remove(f'images/{path}')


class ImageClient:

    def __init__(self, url):
        self.url = url

    def get_images(self, tiempo, verify_path):
        images_array = []
        cantidad = 0  # cantidad de frames
        timestamp_salida = time.time() + tiempo
        s = r.Session()
        while time.time() < timestamp_salida:
            response = s.get(url=self.url, stream=True,
                             verify=verify_path.name)
            images_array.append(response.content)
        s.close()
        for image in images_array:
            f = open(f'images/{cantidad}.jpg', "wb")
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
        print(document)
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

    def get_events_duration(self, collection: str) -> dict:
        db = self.client[self.event_db]
        collection = db[collection]
        document = collection.find_one({"id": 1})
        return document

    def delete_events_duration(self, collection: str, duration: datetime) -> str:
        db = self.client[self.event_db]
        collection = db[collection]
        res = collection.delete_many(
            {
               'date_time': {'$lt': dt.isoformat(duration)}
            })
        print(res.raw_result)
        return res.raw_result

    def get_cert_content(self, collection, device_ip):
        db = self.client[self.event_db]
        collection = db[collection]
        document = collection.find_one({"ip_address": device_ip})
        if document is not None:
            return document
        else:
            return {'msg': 'Not found'}

