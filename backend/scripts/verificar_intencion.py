"""Verificacion manual de la clasificacion de intencion tras el fix."""
import asyncio
import warnings

warnings.filterwarnings("ignore")

from main import app  # noqa: F401
from app.modules.chat_engine.intent_classifier import IntentClassifier

CASOS = [
    ("Gracias, ya tengo los datos", "greeting"),
    ("Perfecto, esos registros me sirven", "greeting"),
    ("Gracias, revisaré el total después", "greeting"),
    ("Hola, ¿cuántas ventas hubo?", "data_analysis"),
    ("Hola, quiero ver las ventas de enero", "data_analysis"),
    ("Hola, muéstrame el total de clientes", "data_analysis"),
    ("Hola, explícame qué es el margen", "explanation"),
]

ok = True
for q, esperado in CASOS:
    got = asyncio.run(IntentClassifier.classify_intent(q))
    marca = "OK " if got == esperado else "MALO"
    if got != esperado:
        ok = False
    print(f"  [{marca}] {q[:42]:44} -> {got}  (esperado {esperado})")

print()
print("TODOS CORRECTOS" if ok else "HAY DISCREPANCIAS")
raise SystemExit(0 if ok else 1)
