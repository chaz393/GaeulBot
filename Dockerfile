FROM python:3.8.0

RUN pip3 install instaloader discord psycopg2 pytz
RUN mkdir /src

ADD src/  /src/

CMD ["python3", "-u", "/src/GaeulBot.py"]
