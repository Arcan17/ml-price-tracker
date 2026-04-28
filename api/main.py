from fastapi import FastAPI

app = FastAPI(title="ML Price Tracker", docs_url=None, redoc_url=None)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ml-price-tracker"}


@app.get("/")
def root():
    return {"status": "ok"}
