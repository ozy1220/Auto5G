from cgitb import reset
from distutils.filelist import translate_pattern
from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.encoders import jsonable_encoder
import uvicorn
import asyncio
import aiofiles
import datetime
import uuid
import random
import time
from starlette.responses import RedirectResponse
from coord import coordenadas
import auxiliares
from auxiliares import SIN_CONEXION, carros
import math
import timeit
import logging



# -------- Inicia codigo para SSE
from sse_starlette.sse import EventSourceResponse
# -------- Fin codigo para SSE

app = FastAPI()
#del 0-2 van a ser los sensores de el frente
#del 3-5 van a ser los sensores traseros

qPosiciones = asyncio.Queue(maxsize = 5000)

# ---------- Termina codigo para SSE
STREAM_DELAY = 1  # second
RETRY_TIMEOUT = 15000  # milisecond


# ------------  AUXILIARES

def actualizaEstadoCarro(carro):
    estado = auxiliares.validaEstadoCarro(carro)
    if estado != auxiliares.carros[carro].estatus_conexion:
        # Genera estado conexion
        auxiliares.carros[carro].estatus_conexion = estado
        qobj = {
            'tipo': 'connect',
            'carro': carro,
            'status': carros[carro].ocupado,
            'conexion': estado
        }
        qPosiciones.put_nowait(qobj)


def validaCarros():
    actualizaEstadoCarro('Rojo')
    actualizaEstadoCarro('Verde')
    actualizaEstadoCarro('Azul')

# ------------  FIN AUXILIARES



@app.get('/stream')
async def message_stream(request: Request):
    async def event_generator():
        while True:
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break

            # Checks for new messages and return them to client if any
            try:
                qobj = await asyncio.wait_for(qPosiciones.get(), 300)
            except:
                # Si no hubo eventos, no mandes nada.
                continue

            print(qobj)
            color = qobj['carro']
            tipo = qobj['tipo']

            if tipo == 'message':
                front = qobj['front']
                back = qobj['back']
                coordx = int(qobj['coordx'])
                coordy = int(qobj['coordy'])
                rad = qobj['rad'] 
                datastr = '{"color": "' + color + '", "front": ' + str(front) + ', "back": ' + str(back) + ', "coordx": ' + str(coordx) +', "coordy": ' + str(coordy) +', "rad": ' + str(rad) + '}'
            elif tipo == 'connect':
                status = qobj['status']
                conexion = qobj['conexion']
                datastr = '{"color": "' + color + '", "status": ' + status + ', "conexion": ' + str(conexion) + '}'
            
            eobj = {
                    'event': tipo,
                    'id': 'message_id',
                    'retry': RETRY_TIMEOUT,
                    'data': datastr
            }
            yield eobj

            #await asyncio.sleep(STREAM_DELAY)

    return EventSourceResponse(event_generator())
# ---------- Fin codigo para SSE


@app.get("/", response_class=HTMLResponse)
async def root():

    if carros['Rojo'].ocupado == 'true': linkRojo = '#'
    else: linkRojo = '/control/Rojo'
    if carros['Azul'].ocupado == 'true': linkAzul = '#'
    else: linkAzul = '/control/Azul'
    if carros['Verde'].ocupado == 'true': linkVerde = '#'
    else: linkVerde = '/control/Verde'

    async with aiofiles.open("./archivosHTML/inicio.html", mode="r") as f:
        html = await f.read()

    html = html.format(ocupadoRojo = carros['Rojo'].ocupado, 
                       ocupadoAzul = carros['Azul'].ocupado,
                       ocupadoVerde = carros['Verde'].ocupado,
                       linkRojo = linkRojo,
                       linkAzul = linkAzul,
                       linkVerde = linkVerde)
    return HTMLResponse(content=html, status_code=200)


@app.get("/admin", response_class=HTMLResponse)
async def pagAdmin():
    async with aiofiles.open('./archivosHTML/principal.html', mode='r') as f:
    # f = open("./archivosHTML/principal.html", "r")
        html = await f.read()

    return HTMLResponse(content=html, status_code=200)


@app.get("/avanzaMotores/{carro}")
async def _avanza(carro):

    # seccion de heartbeats
    auxiliares.heartbeatMotores(carro)
    validaCarros()

    try:

        res = await asyncio.wait_for(auxiliares.carros[carro].queue.get(), timeout = 10.0)
        auxiliares.carros[carro].dire = res
        auxiliares.carros[carro].queue.task_done()
        
        dir_nueva = auxiliares.overrideDireccion(carro, res)
        logging.warning(f'{time.time()} Res /avanzaMotores/{carro} :  res = {res}, dir_final = {dir_nueva}')
        return str(dir_nueva) 

    except asyncio.TimeoutError:
        auxiliares.carros[carro].dire = 'V'
        return str('V')


@app.get("/confirmaEnlace/{carro}")
async def _confirmaEnlace(carro):
    logging.warning(f'Se confirma enlace de carro {carro}')
    return "OK"
    

@app.get("/control/{carro}", response_class=HTMLResponse)
async def _carrito(carro):
    x = str(uuid.uuid4())
    carros[carro].llave = x
    carros[carro].ocupado = 'true'
    qobj = {
        'tipo': 'connect',
        'carro': carro,
        'status': 'true',
        'conexion': carros[carro].estatus_conexion
    }
    qPosiciones.put_nowait(qobj)
    while not carros[carro].queue.empty(): 
        carros[carro].queue.get_nowait()
        carros[carro].queue.task_done()

    carros[carro].seccion_f = -1
    carros[carro].seccion_a = -1
    carros[carro].sentido = auxiliares.LIMBO
    auxiliares.eliminaProhibidos(carro)

    async with aiofiles.open("./archivosHTML/control.html", mode="r") as f:
        html = await f.read()
    html = html.format(carro = carro,
                       hash = x)
    return HTMLResponse(content = html, status_code=200)


@app.get("/desconecta/{carro}")
async def _desconecta(carro, status_code = 200):
    carros[carro].ocupado = 'false'
    carros[carro].llave = str(uuid.uuid4())
    qobj = {
        'tipo': 'connect',
        'carro': carro,
        'status': 'false',
        'conexion': carros[carro].estatus_conexion
    }
    qPosiciones.put_nowait(qobj)
    
    return RedirectResponse(url="/",status_code=302)


@app.get("/direccion/{param_dir}/{carro}/{hash}")
async def direccion(response: Response, param_dir, carro, hash):
    response.headers["access-control-allow-origin"] = "*"

    if (hash != 'admin' and hash != auxiliares.carros[carro].llave): 
        return "Error(no eres quien lo controla)"
    else:
        if not auxiliares.carros[carro].queue.full():
            auxiliares.carros[carro].queue.put_nowait(param_dir)
            print(f'{time.time()} Enviando a cola de carro {carro} direccion {param_dir}')
            return 'OK'
        else:
            logging.warning(f'La cola de instrucciones del carro {carro} esta llena')

@app.get("/img/{archivo}", response_class=FileResponse)
async def _sirvearchivo(archivo):
    return FileResponse(f"./img/{archivo}")


@app.get("/posicion/{carro}/{front}/{back}")
async def _posicion(carro,front,back):
    # logging
    logging.warning(f'{time.time()} - /posicion/{carro}/{front}/{back}')

    posx, posy, angulo, prohibe = auxiliares.calculaSeccion(carro, front, back)
    logging.warning(f'{time.time()} - prohibe = {prohibe}, seccionf = {carros[carro].seccion_f}, secciona = {carros[carro].seccion_a}')
    if prohibe:
        if not auxiliares.carros[carro].queue.full:
            auxiliares.carros[carro].queue.put_nowait(auxiliares.DIR_PARA)
        else:
            logging.error(f'Se intento forzar detencion en carro {carro} pero su cola de instrucciones esta llena')

    # seccion de heartbeats
    auxiliares.heartbeatPosicion(carro)
    validaCarros()

    qobj = {
        'tipo': 'message',
        'carro': carro,
        'front': front,
        'back': back,
        'coordx': posx,
        'coordy': posy,
        'rad': angulo
    }
    qPosiciones.put_nowait(qobj)

    return "acabe"

@app.get("/registraArduino/{carro}/{tipo}")
async def registraArduino(carro, tipo, request: Request):
    if tipo == "posicion":
        carros[carro].ipPosiciones = request.client.host
        if carros[carro].ipMotores != "":
            return carros[carro].ipMotores
        else:
            return "F"
    elif tipo == "motores":
        carros[carro].ipMotores = request.client.host
        return "OK"


@app.get("/velocidad/{carro}")
async def velocidad(carro):
    st = auxiliares.vel['vh'] + auxiliares.vel['vl'] + auxiliares.vel['vn']
    return st


if __name__ == '__main__':
    logging.basicConfig(filename = "logfile.log", level = logging.WARNING)
    uvicorn.run(app, host='0.0.0.0', port='8080')