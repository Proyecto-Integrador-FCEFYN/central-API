# Etapa 1: Instalación de dependencias que rara vez cambian
FROM python:3.8-bullseye AS base
ENV FLASK_APP=app
EXPOSE 80 443 27017
LABEL maintainer="agustincarranza@mi.unc.edu.ar, fd.dandrea@unc.edu.ar"
RUN apt-get update && \
    apt-get install -y ffmpeg libsm6 libxext6 && \
    rm -rf /var/lib/apt/lists/*
RUN mkdir "/app"
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# Etapa 2: Construcción de la aplicación
FROM base AS app
COPY . /app
RUN ln -sf /usr/share/zoneinfo/America/Argentina/Buenos_Aires /etc/localtime && \
    echo "America/Argentina/Buenos_Aires" > /etc/timezone

CMD ["gunicorn", "-w", "4", "--bind", "0.0.0.0:5000", "wsgi:app"]