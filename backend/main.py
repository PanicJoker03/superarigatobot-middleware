# fast api example middleware to link watson assistant x to knowledge base
from fastapi import FastAPI

app = FastAPI()

@app.get("/product/{handle}")
async def get_product(handle: str):
    # Query Shopify here
    return {
        "name": "Gojo Figure",
        "price": "39.99",
        "available": True
    }