from cgitb import reset
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
import datetime

app = FastAPI()
#del 0-2 van a ser los sensores de el frente
#del 3-5 van a ser los sensores traseros
carros = {
    'Azul':{
        'frente': -1,
        'atras': -1,
        'dire': 'V',
        'queue': asyncio.Queue()
    },
    'Verde':{
        'frente': -1,
        'atras': -1,
        'dire': 'V',
        'queue': asyncio.Queue()
    },
    'Rojo':{
        'frente': -1,
        'atras': -1,
        'dire': 'V',
        'queue': asyncio.Queue()
    }
}

@app.get("/")
async def root():
    return {"message": "Hello World!"}

@app.get("/avanzaMotores/{carro}")
async def _avanza(carro):
    print(datetime.datetime.now())
    try:
        res = await asyncio.wait_for(carros[carro]['queue'].get(), timeout = 50.0)
        carros[carro]['queue'].task_done()
        carros[carro]['dire'] = res
        print(res)
        return str(res)
    except asyncio.TimeoutError:
        carros[carro]['dire'] = 'V'
        print(carros[carro]['dire'])
        return str('V')


@app.get("/control/", response_class=HTMLResponse)
async def _carrito():
    f = open("./archivosHTML/control.html", "r")
    html = f.read()
    print(html)
    return HTMLResponse(content = html, status_code=200)


@app.get("/direccion/{param_dir}/{carro}")
async def direccion(response: Response, param_dir, carro):
    response.headers["access-control-allow-origin"] = "*"

    global carros
    carros[carro]['queue'].put_nowait(param_dir)
    return 'OK'

@app.get("/posicion/{carro}/{front}/{back}")
async def _posicion(carro,front,back):
    
    print(datetime.datetime.now())

    global carros
    carros[carro]['frente'] = front
    carros[carro]['atras'] = back

    if carros[carro]['dire'] == 'N': carros[carro]['queue'].put_nowait('S')
    else: carros[carro]['queue'].put_nowait('N') 
    
    return "acabe"



if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port='8080')