import uuid
import cv2
import os
import requests as r
import time
from pymongo import MongoClient
from bson.binary import Binary
import gridfs


class ImageToVideo:

    def __init__(self, filename):
        self.filename = filename

    def video_from_images(self, fps):
        image_folder = 'images'
        # video_name = 'video.avi'

        images = [img for img in os.listdir(image_folder) if img.endswith(".jpg")]
        images.sort()
        frame = cv2.imread(os.path.join(image_folder, images[0]))
        height, width, layers = frame.shape

        video = cv2.VideoWriter(f'videos/{self.filename}', 0, fps, (width, height))

        for image in images:
            video.write(cv2.imread(os.path.join(image_folder, image)))

        cv2.destroyAllWindows()
        video.release()

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

    def get_images(self, tiempo):
        images_array = []
        cantidad = 0  # cantidad de frames
        timestamp_salida = time.time() + tiempo
        while time.time() < timestamp_salida:
            response = r.get(url=self.url, stream=True)
            images_array.append(response.content)
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
        db = self.client['tesis']
        # collection = db['files']
        fs = gridfs.GridFS(db)
        document = fs.find_one(search_dict)
        if document is None:
            return FileNotFoundError
        print(f'Se encontro un archivo con nombre: {document.filename}')
        binary_data = document.read()
        with open(f'videos/{document.filename}', "wb") as f:
            data = Binary(binary_data)
            f.write(data)
        print(f" El archivo {document.filename} ha sido guardado")
        return document

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
