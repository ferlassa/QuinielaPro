import asyncio
from scraper import init_data

if __name__ == "__main__":
    print("Iniciando carga de datos interna en Railway...")
    asyncio.run(init_data())
    print("Carga completada.")
