from cgitb import reset
from distutils.filelist import translate_pattern
from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.encoders import jsonable_encoder
import uvicorn
import asyncio
import aiofiles
import datetime
import uuid
import random
from starlette.responses import RedirectResponse
from coord import coordenadas

# -------- Inicia codigo para SSE
from sse_starlette.sse import EventSourceResponse
# -------- Fin codigo para SSE

app = FastAPI()
#del 0-2 van a ser los sensores de el frente
#del 3-5 van a ser los sensores traseros
carros = {
    'Azul':{
        'frente': -1,
        'atras': -1,
        'dire': 'V',
        'ocupado': 'false',
        'llave' : '123456',
        'queue': asyncio.Queue()
    },
    'Verde':{
        'frente': -1,
        'atras': -1,
        'dire': 'V',
        'ocupado': 'false',
        'llave' : '123456',
        'queue': asyncio.Queue()
    },
    'Rojo':{
        'frente': -1,
        'atras': -1,
        'dire': 'V',
        'ocupado': 'false',
        'llave' : '123456',
        'queue': asyncio.Queue()
    }
}
qPosiciones = asyncio.Queue()

# ---------- Inicio codigo para SSE
STREAM_DELAY = 1  # second
RETRY_TIMEOUT = 15000  # milisecond

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
                qobj = {
                    'tipo': 'message',
                    'carro': 'Rojo',
                    'front': 1,
                    'back': 100
                }
            color = qobj['carro']
            tipo = qobj['tipo']

            if tipo == 'message':
                front = qobj['front']
                back = qobj['back']
                datastr = '{"color": "' + color + '", "front": ' + str(front) + ', "back": ' + str(back) + '}'
            elif tipo == 'connect':
                status = qobj['status']
                datastr = '{"color": "' + color + '", "status": ' + status + '}'
            
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

    if carros['Rojo']['ocupado'] == 'true': linkRojo = '#'
    else: linkRojo = '/control/Rojo'
    if carros['Azul']['ocupado'] == 'true': linkAzul = '#'
    else: linkAzul = '/control/Azul'
    if carros['Verde']['ocupado'] == 'true': linkVerde = '#'
    else: linkVerde = '/control/Verde'

    async with aiofiles.open("./archivosHTML/inicio.html", mode="r") as f:
        html = await f.read()

    html = html.format(ocupadoRojo = carros['Rojo']['ocupado'], 
                       ocupadoAzul = carros['Azul']['ocupado'],
                       ocupadoVerde = carros['Verde']['ocupado'],
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
    try:
        res = await asyncio.wait_for(carros[carro]['queue'].get(), timeout = 50.0)
        carros[carro]['queue'].task_done()
        carros[carro]['dire'] = res
        return str(res)
    except asyncio.TimeoutError:
        carros[carro]['dire'] = 'V'
        return str('V')


@app.get("/control/{carro}", response_class=HTMLResponse)
async def _carrito(carro):
    x = str(uuid.uuid4())
    carros[carro]['llave'] = x
    carros[carro]['ocupado'] = 'true'
    qobj = {
        'tipo': 'connect',
        'carro': carro,
        'status': 'true'
    }
    qPosiciones.put_nowait(qobj)
    while not carros[carro]['queue'].empty(): 
        carros[carro]['queue'].get_nowait()
        carros[carro]['queue'].task_done()

    async with aiofiles.open("./archivosHTML/control.html", mode="r") as f:
        html = await f.read()
    html = html.format(carro = carro,
                       hash = x)
    return HTMLResponse(content = html, status_code=200)


@app.get("/desconecta/{carro}")
async def _desconecta(carro, status_code = 200):
    carros[carro]['ocupado'] = 'false'
    carros[carro]['llave'] = str(uuid.uuid4())
    qobj = {
        'tipo': 'connect',
        'carro': carro,
        'status': 'false'
    }
    qPosiciones.put_nowait(qobj)
    
    return RedirectResponse(url="/",status_code=302)


@app.get("/direccion/{param_dir}/{carro}/{hash}")
async def direccion(response: Response, param_dir, carro, hash):
    response.headers["access-control-allow-origin"] = "*"

    if (hash != carros[carro]['llave']): return "Error(no eres quien lo controla)"

    carros[carro]['queue'].put_nowait(param_dir)
    return 'OK'


@app.get("/posicion/{carro}/{front}/{back}")
async def _posicion(carro,front,back):

    carros[carro]['frente'] = front
    carros[carro]['atras'] = back
    qobj = {
        'tipo': 'message',
        'carro': carro,
        'front': front,
        'back': back
    }
    qPosiciones.put_nowait(qobj)
    
    return "acabe"


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port='8080')