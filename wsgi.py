#!/usr/bin/python3

from app.app import app as app


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)