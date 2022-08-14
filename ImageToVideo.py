import cv2
import os
import requests as r
import time
from datetime import datetime
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson.binary import Binary
import gridfs


class ImageToVideo:

    def __init__(self, video_path):
        self.video = video_path

    def video_from_images(self, fps):
        image_folder = 'images'
        # video_name = 'video.avi'

        images = [img for img in os.listdir(image_folder) if img.endswith(".jpg")]
        images.sort()
        frame = cv2.imread(os.path.join(image_folder, images[0]))
        height, width, layers = frame.shape

        video = cv2.VideoWriter(f'videos/{self.video}', 0, fps, (width, height))

        for image in images:
            video.write(cv2.imread(os.path.join(image_folder, image)))

        cv2.destroyAllWindows()
        video.release()


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
            cantidad += 1
        for image in images_array:
            f = open(f'images/{time.time()}.jpg', "wb")
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

    def __init__(self, connection_string):
        self.connection_string = connection_string

    def connect(self):
        self.client = MongoClient(self.connection_string,
                                  tls=True,
                                  tlsCertificateKeyFile='config/agustin2022.pem',
                                  server_api=ServerApi('1'))

    def connect_local(self):
        self.client = MongoClient(self.connection_string)

    def save_to_db_grid(self, filename):
        db = self.client['tesis']
        fs = gridfs.GridFS(db)
        with open(f'videos/{filename}', "rb") as f:
            encoded = Binary(f.read())
        file_id = fs.put(data=encoded, filename=filename)
        print(f'the file with id: {file_id} has been saved')
        return file_id

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

    def load_event_file(self, filename, database='eventos'):
        db = self.client[database]
        fs = gridfs.GridFS(db)
        document = fs.find_one({
            "filename": filename
        })
        print(document)
        binary_data = document.read()
        print(f" El archivo {document.filename} ha sido encontrado")
        return Binary(binary_data)

    def save_event_file(self, filename, database='eventos'):
        db = self.client[database]
        fs = gridfs.GridFS(db)
        with open(f'test.png', "rb") as f:
            encoded = Binary(f.read())
        file_id = fs.put(data=encoded, filename=filename)
        print(f'the file with id: {file_id} has been saved')
        return file_id
