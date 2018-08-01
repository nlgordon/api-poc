from asyncio import sleep
from datetime import datetime
from io import BytesIO
import random

import os

import multiprocessing

import sqlalchemy
from PIL import Image
from aiopg.sa import create_engine
from sanic import Sanic, response
from sanic.response import json

app = Sanic()

metadata = sqlalchemy.MetaData()

polls = sqlalchemy.Table('sanic_polls', metadata,
                 sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
                 sqlalchemy.Column('question', sqlalchemy.String(50)),
                 sqlalchemy.Column("pub_date", sqlalchemy.DateTime))


@app.listener('before_server_start')
async def get_engine(app, loop):
    connection = get_connection_string()
    app.engine = await create_engine(connection, maxsize=1000)
    async with app.engine.acquire() as conn:
        ret = []
        async for row in conn.execute("SELECT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'postgres' and tablename = 'sanic_polls')"):
            ret.append(row)

        if not ret:
            await conn.execute("DROP TABLE IF EXISTS sanic_polls")
            await conn.execute("""CREATE TABLE sanic_polls (
                                                    id serial primary key,
                                                    question varchar(50),
                                                    pub_date timestamp
                                                );""")
            for i in range(0, 100):
                await conn.execute(
                    polls.insert().values(question=i,
                                          pub_date=datetime.now())
                )


@app.listener('after_server_stop')
async def close_db(app, loop):
    app.engine.close()
    await app.engine.wait_closed()


def get_connection_string():
    return 'postgres://{0}:{1}@{2}/{3}'.format(os.environ.get('RDS_USERNAME', 'postgres'),
                                               os.environ.get('RDS_PASSWORD', 'password'),
                                               os.environ.get('RDS_HOSTNAME', 'localhost'),
                                               os.environ.get('RDS_DB_NAME', 'postgres'))


@app.route("/hello")
async def hello(request):
    return json({"hello": "world"})


@app.route('/sleepy')
async def sleepy(request):
    sleep_time = random.randint(0, 2000)
    await sleep(sleep_time / 1000)
    return json({"sleepy": str(sleep_time)[0:5]})


@app.route('/sleepy-fixed')
async def sleepy(request):
    sleep_time = int(request.args['sleep'][0])
    await sleep(sleep_time / 1000)
    return json({"sleepy": str(sleep_time)[0:5]})


@app.route("/image")
async def gen_image(request):
    start = datetime.now()
    encoded_png = generate_image()
    end = datetime.now()
    duration = (end - start).microseconds / 1000
    print("Image generation time: {}".format(int(duration)))
    return response.raw(encoded_png, headers={'Content-Type': 'image/png'})


@app.route("/database")
async def query_db(request):
    async with app.engine.acquire() as conn:
        result = []
        async for row in conn.execute(polls.select()):
            result.append({"question": row.question, "pub_date": row.pub_date})
        return json({"polls": result})


def generate_image():
    image = Image.new('RGBA', (256, 256))
    for i in range(0, 100):
        image.putpixel((rand_value(), rand_value()), (rand_value(), rand_value(), rand_value(), rand_value()))
    bytes_io = BytesIO()
    image.save(bytes_io, 'PNG')
    encoded_png = bytes_io.getvalue()
    return encoded_png


def rand_value():
    return random.randint(0, 255)


if __name__ == '__main__':
    port = os.environ.get('SERVING_PORT', 8001)
    cores = multiprocessing.cpu_count()
    if not cores:
        cores = 1

    # cores = 1

    workers = os.environ.get('API_WORKERS', cores * 2)
    app.run(host='0.0.0.0', port=port, workers=workers)
