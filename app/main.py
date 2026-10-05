from fastapi import FastAPI

app = FastAPI(title="Chatbot API", version="0.1.0")

@app.get("/")
async def root():
    return {"message": "Hello World"}



@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}