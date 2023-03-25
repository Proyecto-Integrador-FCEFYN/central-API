FROM python:3.8-bullseye

ENV FLASK_APP=app

EXPOSE 80 443 27017

LABEL maintainer="agustincarranza@mi.unc.edu.ar"

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6 -y

RUN mkdir "/app"

COPY requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r /app/requirements.txt

COPY . /app

RUN pwd

RUN ls -l

RUN ls app

RUN echo ${PATH}

CMD [ "gunicorn", "-w", "4", "--bind", "0.0.0.0:5000", "wsgi:app"]
