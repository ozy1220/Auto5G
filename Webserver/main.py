from cgitb import reset
from distutils.filelist import translate_pattern
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
import datetime
import uuid
from starlette.responses import RedirectResponse

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


@app.get("/", response_class=HTMLResponse)
async def root():

    if carros['Rojo']['ocupado'] == 'true': linkRojo = '#'
    else: linkRojo = '/control/Rojo'
    if carros['Azul']['ocupado'] == 'true': linkAzul = '#'
    else: linkAzul = '/control/Azul'
    if carros['Verde']['ocupado'] == 'true': linkVerde = '#'
    else: linkVerde = '/control/Verde'

    f = open("./archivosHTML/inicio.html", "r")
    html = f.read()
    html = html.format(ocupadoRojo = carros['Rojo']['ocupado'], 
                       ocupadoAzul = carros['Azul']['ocupado'],
                       ocupadoVerde = carros['Verde']['ocupado'],
                       linkRojo = linkRojo,
                       linkAzul = linkAzul,
                       linkVerde = linkVerde)
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
    print(x)

    f = open("./archivosHTML/control.html", "r")
    html = f.read()
    html = html.format(carro = carro,
                       hash = x)
    return HTMLResponse(content = html, status_code=200)


@app.get("/desconecta/{carro}")
async def _desconecta(carro, status_code = 200):
    carros[carro]['ocupado'] = 'false'
    carros[carro]['llave'] = str(uuid.uuid4())
    return RedirectResponse(url="/",status_code=302)


@app.get("/direccion/{param_dir}/{carro}/{hash}")
async def direccion(response: Response, param_dir, carro, hash):
    response.headers["access-control-allow-origin"] = "*"

    if (hash != carros[carro]['llave']): return "Error(no eres quien lo controla)"

    carros[carro]['queue'].put_nowait(param_dir)
    return 'OK'


@app.get("/posicion/{carro}/{front}/{back}")
async def _posicion(carro,front,back):
    
    print(datetime.datetime.now())

    global carros
    carros[carro]['frente'] = front
    carros[carro]['atras'] = back

    carros[carro]['dire'] = 'S'
    
    return "acabe"


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port='8080')