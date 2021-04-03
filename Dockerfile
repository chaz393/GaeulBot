FROM python:3.7.7

RUN pip3 install instaloader discord psycopg2

ADD src/__main__.py /__main__.py

CMD ["python3", "/__main__.py"]