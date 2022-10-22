# README

## Instrucciones

Copiar certificados para MongoDB en ./config

## COMANDOS
```bash
git clone git@github.com:Proyecto-Integrador-FCEFYN/central-API.git
cd central-API
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m flask run --host=0.0.0.0 --port=5000
```

## REQUERIMIENTOS

```bash
sudo apt update
sudo apt install -y ffmpeg
```

### Para levantar con gunicorn:
Esto deberia estar en dockerfile y apuntarlo con el nginx
```bash
gunicorn -w 4 -b localhost:6000 'app:app'
```