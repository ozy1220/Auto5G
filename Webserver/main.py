from cgitb import reset
from difflib import restore
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
from auxiliares import SIN_CONEXION, bloques, carros, cx_seccion, cy_calle, ang_calle
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

    logging.warning(f'{time.time()} - Se recibio peticion /avanzaMotores/{carro}')

    # seccion de heartbeats
    auxiliares.heartbeatMotores(carro)
    validaCarros()

    try:
        # Si la cola esta vacia, el control tiene un comando apretado y lo ultimo que se envio al coche es distinto de ese comando, enviale el comando al coche
        if carros[carro].queue.empty() and carros[carro].dirControl != auxiliares.DIR_PARA and carros[carro].dirControl != carros[carro].ultDir:
            logging.warning(f'{time.time()} - Mandando comando ficticio por cola vacia y control apretado {carros[carro].dirControl}')
            carros[carro].ultDir = carros[carro].dirControl
            res = carros[carro].dirControl
        else:
            # Si la cola tiene datos, entonces envia el primer dato de forma inmediata sin detener
            if not carros[carro].queue.empty():
                res = carros[carro].queue.get_nowait()
                carros[carro].queue.task_done()

            # Si no hay comandos en la cola, espera a que llegue el siguiente
            else:
                res = await asyncio.wait_for(carros[carro].queue.get(), timeout=5)
                carros[carro].queue.task_done()
        
        # Antes de enviar el comando al carro, valida si hay alguna prohibicion que sobreescriba dicho comando
        dir_nueva = auxiliares.overrideDireccion(carro, res)
        
        # Actualiza la ultima direccion que se envia al carro y si no es ajuste el numero de ajustes seguidos
        carros[carro].ultDir = dir_nueva
        if dir_nueva not in auxiliares.direccionesAjuste:
            carros[carro].ajustesSeguidos = 0

        logging.warning(f'{time.time()} Respuesta a /avanzaMotores/{carro} :  res = {res}, dir_final = {dir_nueva}')
        respuesta=str(dir_nueva) 

    except asyncio.TimeoutError:
        logging.warning(f'{time.time()} - Timeout para /avanzaMotores/{carro}. Se enviara ' + auxiliares.DIR_PARA )
        respuesta=auxiliares.DIR_PARA

    if respuesta == 'V': code = 200
    elif respuesta == 'N': code = 201
    elif respuesta == 'S': code = 202
    elif respuesta == 'E': code = 203
    elif respuesta == 'O': code = 204
    elif respuesta == 'W': code = 205
    elif respuesta == 'X': code = 206
    elif respuesta == 'Y': code = 207
    elif respuesta == 'Z': code = 208
    elif respuesta == 'D': code = 209
    elif respuesta == 'U': code = 210
      
    if respuesta == 'D' or respuesta == 'U': carros[carro].ultDir = 'V'
    else: carros[carro].ultDir = respuesta

    return Response(status_code=code)


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
    auxiliares.queuePush(carro, auxiliares.DIR_PARA, True)

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
        carros[carro].dirControl = param_dir
        auxiliares.queuePush(carro, param_dir, False)
        logging.warning(f'{time.time()} Se agrego direccion {param_dir} a la cola del carro {carro}')
        return 'OK'


@app.get("/img/{archivo}", response_class=FileResponse)
async def _sirvearchivo(archivo):
    return FileResponse(f"./img/{archivo}")


@app.get("/posicion/{carro}/{front}/{back}")
async def _posicion(carro,front,back):
    # logging
    logging.warning(f'{time.time()} - Posicion {carro}. Frente de {carros[carro].frente} -> {front}. Atras de {carros[carro].atras} -> {back}')

    # seccion de heartbeats
    auxiliares.heartbeatPosicion(carro)
    validaCarros()

    calle = 2

    dirControl = carros[carro].dirControl
    filf = coordenadas[front]['y']
    colf = coordenadas[front]['x']
    filb = coordenadas[back]['y']
    colb = coordenadas[back]['x']

    # Calcula la orientacion y la calle del carro
    if colf == colb:
        if filf > filb: ang = math.pi / 2
        else: ang = math.pi * 3 / 2
    else:
        pend = (filf - filb) / (colf - colb)
        ang = math.atan(pend)
        
        # Python regresa el angulo entre 90 y 270 grados, asi que hay que ver si el carro iba o venia sobre esa pendiente
        if ang == 0 and colf < colb: ang += math.pi
        elif ang < 0 and (filf - filb) > 0: ang += math.pi
        elif ang > 0 and (filf - filb) < 0: ang += math.pi
    
    if ang < 0:
        ang += 2.0 * math.pi

    if ang >= math.pi * 7 / 4.0 or ang < math.pi / 4.0:
        dirBrujula = 0
    elif ang >= math.pi / 4.0 and ang < math.pi * 3.0 / 4.0:
        dirBrujula = 90
    elif ang >= math.pi * 3.0 / 4.0 and ang < math.pi * 5.0 / 4.0:
        dirBrujula = 180
    else:
        dirBrujula = 270
    logging.warning(f'{time.time()} - Se calculo angulo {ang}, brujula {dirBrujula}, xf {colf}, yf {filf}, xb {colb}, yb {filb}')

    # Ubica en que calle esta y en base a eso decide los carriles
    chf = coordenadas[front]['ch']
    cvf = coordenadas[front]['cv']
    chb = coordenadas[back]['ch']
    cvb = coordenadas[back]['cv']

    if cvf == 0 and cvb == 0:
        carrilf = (int(chf)-1)%7
        carrilb = (int(chb)-1)%7
    elif chf == 0 and chb == 0:
        carrilf = (int(cvf)-1)%7
        carrilb = (int(cvb)-1)%7
    else:
        dfil = abs(filf - filb)
        dcol = abs(colf - colb)
        if dfil > dcol:
            carrilf = (int(cvf)-1)%7
            carrilb = (int(cvb)-1)%7
        else: 
            carrilf = (int(chf)-1)%7
            carrilb = (int(chb)-1)%7             
    

    # Seccion de detonados por posicion
    dirNueva = ""
    limpiaCola = False
    
    # Actualiza los valores del carro
    carros[carro].yf = filf
    carros[carro].xf = colf
    carros[carro].ya = filb
    carros[carro].xa = colb
    carros[carro].dirBrujula = dirBrujula
    carros[carro].angulo = ang

    # Revisa si la posicion detona algun comando debido a la posicion
    tmp = auxiliares.overrideDireccion(carro, dirControl)
    if tmp != dirControl:
        logging.warning(f'{time.time()} - La posicion detono un comando de avance. Direccion del contro = {dirControl}, comando a insertar {tmp}')
        dirNueva = tmp
        limpiaCola = dirNueva == auxiliares.DIR_PARA

    # Decide si es necesario ajustar para centrar en el carril
    if dirNueva == "" and dirControl in auxiliares.direccionesFrente:

        if carrilf == 0: 
            # El carril 0 siempre cierra al centro
            dirNueva = auxiliares.DIR_FL
        elif carrilf == 6:
            dirNueva = auxiliares.DIR_FR
        elif carrilf == 1:
            if (carrilb >= 1): dirNueva = auxiliares.DIR_FL
        elif carrilf == 5: 
            if (carrilb <= 5): dirNueva = auxiliares.DIR_FR
        elif carrilf > 3 and carrilb < 3:
            dirNueva = auxiliares.DIR_FR
        elif carrilf < 3 and carrilb > 3:
            dirNueva = auxiliares.DIR_FL

    elif dirControl in auxiliares.direccionesAtras:
        if carrilb == 0: 
            # El carril 0 siempre cierra al centro
            dirNueva = auxiliares.DIR_BL
        elif carrilb == 6:
            dirNueva = auxiliares.DIR_BR
        elif carrilb == 1:
            if (carrilf >= 1): dirNueva = auxiliares.DIR_BL
        elif carrilb == 5: 
            if (carrilf <= 5): dirNueva = auxiliares.DIR_BR
        elif carrilb > 3 and carrilf < 3:
            dirNueva = auxiliares.DIR_BR
        elif carrilb < 3 and carrilf > 3:
            dirNueva = auxiliares.DIR_BL            
    
    logging.warning(f'Se proceso posicion. Carril F {carrilf}, Carril B {carrilb}, Dir nueva {dirNueva}, Dir control {dirControl}')

    # Si hay una direccion nueva, insertala en la cola
    if dirNueva != "":
        auxiliares.queuePush(carro, dirNueva, limpiaCola)

    # Envia la nueva posicion para la interfaz grafica
    qobj = {
        'tipo': 'message',
        'carro': carro,
        'front': front,
        'back': back,
        'calle': carros[carro].calle,
        'coordy': int((filf + filb) / 2),
        'coordx': int((colf + colb) / 2),
        'rad': ang
    }
    qPosiciones.put_nowait(qobj)

    return "Acabe posicion"


@app.get("/velocidad/{carro}")
async def velocidad(carro):
    st = auxiliares.vel['vh'] + auxiliares.vel['vl'] + auxiliares.vel['vn'] + '$'
    return Response(content=st, media_type="text/plain")


@app.get("/updatezona/{bloque}/{estado}")
async def _updatezona(bloque,estado):
    #lo manda como int o string
    bloques[bloque].estado = int(estado)
    return "ok"


if __name__ == '__main__':
    logging.basicConfig(filename = "logfile.log", level = logging.WARNING)
    uvicorn.run(app, host='0.0.0.0', port='8080', timeout_keep_alive = 60)