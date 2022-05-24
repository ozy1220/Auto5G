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
from starlette.responses import RedirectResponse
from coord import coordenadas
import math

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
                    'back': 100,
                    'coordx':0,
                    'coordy':0,
                    'rad':0
                }
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
        res = await asyncio.wait_for(carros[carro]['queue'].get(), timeout = 20.0)
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

@app.get("/img/{archivo}", response_class=FileResponse)
async def _sirvearchivo(archivo):
    return FileResponse(f"./img/{archivo}")


@app.get("/posicion/{carro}/{front}/{back}")
async def _posicion(carro,front,back):
 
    if (carros[carro]['frente'] != front and carros[carro]['atras'] != back):
        dx = coordenadas[front]['x']-coordenadas[back]['x']
        dy = coordenadas[front]['y']-coordenadas[back]['y']
        px = coordenadas[front]['x']*5/1000
        py = coordenadas[front]['y']*5/1000
    elif carros[carro]['frente'] != front:
        dx = coordenadas[front]['x']-coordenadas[str(carros[carro]['frente'])]['x']
        dy = coordenadas[front]['y']-coordenadas[str(carros[carro]['frente'])]['y']
        px = coordenadas[front]['x']*5/1000
        py = coordenadas[front]['y']*5/1000
    else:
        dx = coordenadas[str(carros[carro]['atras'])]['x'] - coordenadas[front]['x']
        dy = coordenadas[str(carros[carro]['atras'])]['y'] - coordenadas[back]['y']
        px = coordenadas[back]['x']*5/1000
        py = coordenadas[back]['y']*5/1000

    #falta encontrar el centro del carro siguendo la direccion
    if dx == 0:
        if (dy > 0): pend = 0
        else: pend = 180
    elif dy == 0:
        if (dx > 0): pend = 270
        else: pend = 90
    else: 
        pend = -dy/dx
        pend = math.atan(pend)
        if pend < math.pi/2: pend = (math.pi/2)-pend    
        else: pend = (5*math.pi)/2 - pend

    carros[carro]['frente'] = front
    carros[carro]['atras'] = back
    qobj = {
        'tipo': 'message',
        'carro': carro,
        'front': front,
        'back': back,
        'coordx': px,
        'coordy': py,
        'rad': pend
    }
    qPosiciones.put_nowait(qobj)
    
    return "acabe"


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port='8080')