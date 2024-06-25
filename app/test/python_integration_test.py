import inspect
import unittest
import requests
from PIL import Image
import io

def test_result(response, url, condiciones=""):
    calling_function = inspect.stack()[1].function
    if response.status_code == 200:
        print(f'{calling_function} = OK {url}. {condiciones} --> {response.text}')
    else:
        print(f'{calling_function} = FAIL {url}. Código de estado: {response.status_code}. msg: {response.text}')
    
class MyTests(unittest.TestCase):
    user_network_ip = 'ingreso.lac'
    ESP32_IP = '192.168.24.123'
    ESP32_HTTPS_PORT = 443
    ESP32_ID = 3

    def test_1a(self):  # /api/v1/event/rfid
        url = f'http://{self.user_network_ip}:5000/api/v1/event/rfid'
        data = 1541611
        condiciones="RFID: usuario administrador"
        headers = {'Content-Type': 'application/json', 'X-Forwarded-For': self.ESP32_IP}
        response = requests.post(url, json=data, headers=headers)
        test_result(response, url, condiciones)
        self.assertEqual(response.status_code, 200, f"FAIL {url}. Código de estado: {response.status_code}. msg: {response.text}")

    def test_1b(self):  # /api/v1/event/rfid
        url = f'http://{self.user_network_ip}:5000/api/v1/event/rfid'
        data = 3923786
        condiciones="RFID: usuario comun autorizado"
        headers = {'Content-Type': 'application/json', 'X-Forwarded-For': self.ESP32_IP}
        response = requests.post(url, json=data, headers=headers)
        test_result(response, url, condiciones)
        self.assertEqual(response.status_code, 200, f"FAIL {url}. Código de estado: {response.status_code}. msg: {response.text}")
    
    def test_1c(self):  # /api/v1/event/rfid
        url = f'http://{self.user_network_ip}:5000/api/v1/event/rfid'
        data = 3787906
        condiciones="RFID: usuario comun NO autorizado"
        headers = {'Content-Type': 'application/json', 'X-Forwarded-For': self.ESP32_IP}
        response = requests.post(url, json=data, headers=headers)
        test_result(response, url, condiciones)
        self.assertEqual(response.status_code, 200, f"FAIL {url}. Código de estado: {response.status_code}. msg: {response.text}")

    def test_2(self):  # api/v1/event/movimiento
        url = f'http://{self.user_network_ip}:5000/api/v1/event/movimiento'
        headers = {'X-Forwarded-For': self.ESP32_IP}
        response = requests.post(url, headers=headers)
        test_result(response, url)
        self.assertEqual(response.status_code, 200, f"FAIL {url}. Código de estado: {response.status_code}. msg: {response.text}")

    def test_3(self):  # /api/v1/event/timbre
        url = f'http://{self.user_network_ip}:5000/api/v1/event/timbre'
        headers = {'X-Forwarded-For': self.ESP32_IP}
        response = requests.post(url, headers=headers)
        test_result(response, url)
        self.assertEqual(response.status_code, 200, f"FAIL {url}. Código de estado: {response.status_code}. msg: {response.text}")

    def test_4(self):  # /webbutton
        url = f'http://{self.user_network_ip}:5000/api/v1/event/webbutton'
        headers = {'X-Forwarded-For': self.ESP32_IP}
        data = {
            'host': self.ESP32_IP,
            'port': self.ESP32_HTTPS_PORT,
            'user_id': 3,
            'device_id': self.ESP32_ID,
            'usuario': 'usuario-esp32',
            'password': 'password-esp32'
        }
        response = requests.post(url, json=data, headers=headers)
        test_result(response, url)
        self.assertEqual(response.status_code, 200, f"FAIL {url}. Código de estado: {response.status_code}. msg: {response.text}")

    # def test_5(self):  # /api/v1/files
    #     url = f'http://ingreso.lac/api/v1/files/1c603243-3a04-4f6a-a72b-792ed8237145.jpg'
    #     ca_cert_path = './RootCA.crt'
    #     response = requests.post(url, verify=ca_cert_path)
    #     self.assertEqual(response.status_code, 200, f"FAIL {url}. Código de estado: {response.status_code}. msg: {response.text}")

    # def test_6(self):  # /api/v1/streaming
    #     url = f'http://ingreso.lac:5000/api/v1/streaming'
    #     response = requests.get(url)
    #     self.assertEqual(response.status_code, 200, f"FAIL {url}. Código de estado: {response.status_code}. msg: {response.text}")
    #     self.assertTrue(response.headers['Content-Type'].startswith('multipart/x-mixed-replace'))
        
    #     # Guardar la respuesta del endpoint como un GIF
    #     if response.headers['Content-Type'].startswith('multipart/x-mixed-replace'):
    #         images = []
    #         current_image_data = b''
    #         for chunk in response.iter_content(chunk_size=None):
    #             current_image_data += chunk
    #             frame_start_index = current_image_data.find(b'--frame')
    #             if frame_start_index != -1:
    #                 image_data = current_image_data[:frame_start_index]
    #                 image = Image.open(io.BytesIO(image_data))
    #                 images.append(image)
    #                 current_image_data = current_image_data[frame_start_index:]
    #         if images:
    #             images[0].save('video.gif', save_all=True, append_images=images[1:], loop=0)
    #             print("Archivo GIF generado exitosamente.")
    #         else:
    #             print("No se han procesado imágenes.")
    #     else:
    #         print("Error al obtener la secuencia de imágenes.")

if __name__ == '__main__':
    print("Bateria de pruebas integrales")
    unittest.main()
