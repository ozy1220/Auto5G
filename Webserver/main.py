from fastapi import FastAPI, Response

app = FastAPI()
pos = "Desconocida"
dir = 'V'

@app.get("/")
async def root():
    return {"message": "Hello World!"}

#controlador a direccion
#identificador de carro y a donde tiene que moverse
@app.get("/direccion/{param_dir}")
async def direccion(response: Response, param_dir):
    response.headers["access-control-allow-origin"] = "*"
    global dir 
    dir = param_dir
    return "Posicion: " + pos

#lo pide el carro para saber a donde avanzar
#manda la direccion
@app.get("/avanza")
async def _avanza():
    res = dir
    print(res)
    return str(res)

@app.get("/posicion/{p}")
async def _posicion(p):
    global pos
    pos = p
    return pos

@app.get("/querycarro/{p}")
async def _querycarro(p):
    global dir
    global pos
    pos = p
    return dir
    
