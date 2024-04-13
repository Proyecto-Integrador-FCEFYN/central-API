# Etapa 2: Construcción de la aplicación
FROM api-base:v1.0
COPY . /app
RUN ln -sf /usr/share/zoneinfo/America/Argentina/Buenos_Aires /etc/localtime && \
    echo "America/Argentina/Buenos_Aires" > /etc/timezone

CMD ["gunicorn", "-w", "4", "--bind", "0.0.0.0:5000", "wsgi:app"]