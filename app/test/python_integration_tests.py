import inspect
import requests
from requests.auth import HTTPBasicAuth

# setup
user_network_ip='ingreso.lac'
# user_network_ip='localhost'
ESP32_IP='192.168.24.123'
ESP32_HTTPS_PORT=443
ESP32_ID=3
enable_all_test= True

def test_result(response, url):
    calling_function = inspect.stack()[1].function
    if response.status_code == 200:
        print(f'{calling_function} = OK {url}. --> {response.text}')
    else:
        print(f'{calling_function} = FAIL {url}. Código de estado: {response.status_code}. msg: {response.text}')

def test_1(): # /api/v1/event/rfid
    url = f'http://{user_network_ip}:5000/api/v1/event/rfid'
    data= 1541611 
    headers = {'Content-Type': 'application/json', 'X-Forwarded-For': ESP32_IP}
    response = requests.post(url, json=data, headers=headers)  # Realiza la solicitud POST
    test_result(response, url)

def test_2(): # api/v1/event/movimiento
    url = f'http://{user_network_ip}:5000/api/v1/event/movimiento'
    headers = {'X-Forwarded-For': ESP32_IP}
    # Realizar la solicitud POST con la cabecera X-Forwarded-For y los datos en el cuerpo
    response = requests.post(url, headers=headers)
    test_result(response, url)

def test_3(): # /api/v1/event/timbre
    url = f'http://{user_network_ip}:5000/api/v1/event/timbre'
    headers = {'X-Forwarded-For': ESP32_IP}
    response = requests.post(url, headers=headers)
    test_result(response, url)    
    
def test_4(): #/webbutton
    url = f'http://{user_network_ip}:5000/api/v1/event/webbutton'
    headers = {'X-Forwarded-For': ESP32_IP}
    # Definir los datos de la solicitud
    data = {
    'host': ESP32_IP,
    'port': ESP32_HTTPS_PORT,
    'user_id': 3,
    'device_id': ESP32_ID,
    'usuario': 'usuario-esp32',
    'password': 'password-esp32'   
    }
    response = requests.post(url, json=data, headers=headers)
    test_result(response, url)

    

def test_5(): #/api/v1/files
    url = f'http://ingreso.lac/api/v1/files/1c603243-3a04-4f6a-a72b-792ed8237145.jpg'
    ca_cert_path= './RootCA.crt'
    # headers = {'X-Forwarded-For': ESP32_IP}
    response = requests.post(url, verify=ca_cert_path)
    test_result(response, url)

# Run all tests / Uncomment tests tu run
if enable_all_test:
    test_1()
    test_2()
    test_3()
    test_4()
    # test_5()
    # test_6()
    # test_7()
    # test_8()
    # test_9()