FROM python:3.8-bullseye

ENV FLASK_APP=app

LABEL maintainer="agustincarranza@mi.unc.edu.ar"

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6 gunicorn -y

RUN mkdir "/app"

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
# CMD [gunicorn "-w" "4" "-b" "localhost:5000" "'app:app'"]