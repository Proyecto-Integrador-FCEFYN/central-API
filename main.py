# This is a sample Python script.

# Press Mayús+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

from ImageToVideo import ImageToVideo, ImageClient, DatabaseConnection
import json
import pprint


cfg = None

video_name = 'video.avi'
# url = "http://192.168.1.140/video"
url = "https://picsum.photos/200/300"

uri = "mongodb+srv://cluster0.dmmkg.mongodb.net/" \
      "?authSource=%24external&authMechanism=MONGODB-X509&retryWrites=true&w=majority"


def print_hi(name):
    print(f'Hi, {name}')

    # client = ImageClient(url=url)
    # fps = client.get_image(tiempo=6)
    #
    # image_to_video = ImageToVideo(video_name)
    # image_to_video.video_from_images(fps=fps)
    #
    # client.clean_images()

    db = DatabaseConnection(connection_string=uri)
    # db.save_to_db()
    db.connect()
    # db.load_from_db()
    # db.save_to_db_grid()
    db.load_from_db_grid()


def load_json():
    with open("config.json") as json_data_file:
        data = json.load(json_data_file)
    pprint.pprint(data)
    return data


if __name__ == '__main__':
    print_hi('PyCharm')
    cfg = load_json()
