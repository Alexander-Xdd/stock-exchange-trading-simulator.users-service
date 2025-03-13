from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from config import SERVER_PORT, SERVER_HOST, SERVER_LOG_LEVEL


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Укажите домен вашего фронтенда
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы
    allow_headers=["*"],  # Разрешить все заголовки
)

@app.get("/")
async def root():
    return {"message": "Hello World"}




if __name__ == "__main__":
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level=SERVER_LOG_LEVEL)