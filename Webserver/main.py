from cgitb import reset
from fastapi import FastAPI, Response
import uvicorn

app = FastAPI()
#del 0-2 van a ser los sensores de el frente
#del 3-5 van a ser los sensores traseros
carros = {
    'Azul':{
        'frente': -1,
        'atras': -1,
        'dire': 'V'
    },
    'Verde':{
        'frente': -1,
        'atras': -1,
        'dire': 'V'
    },
    'Rojo':{
        'frente': -1,
        'atras': -1,
        'dire': 'V'
    }
}

#definepruebas
prueba = "N"

def cambia():
    global prueba
    if prueba == 'N': prueba = 'S'
    elif prueba == 'S': prueba = 'N'

@app.get("/")
async def root():
    return {"message": "Hello World!"}

@app.get("/avanzaMotores/{carro}")
async def _avanza(carro):
    #res = carros[carro]['dire']
    global prueba
    res = prueba
    print(res)
    return str(res)

@app.get("/posicion/{carro}/{front}/{back}")
async def _posicion(carro,front,back):
    
    global carros
    carros[carro]['frente'] = front
    carros[carro]['atras'] = back
    cambia()
    return "acabe"


@app.get("/direccion/{param_dir}/{carro}")
async def direccion(response: Response, param_dir, carro):
    response.headers["access-control-allow-origin"] = "*"

    global carros
    carros[carro]['dire'] = param_dir

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port='8080')