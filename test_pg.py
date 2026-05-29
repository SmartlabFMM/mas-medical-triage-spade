from dotenv import dotenv_values
import os
from pathlib import Path

env_path = Path(".env")
# Cela lit le fichier comme un dictionnaire sans toucher aux variables système
config = dotenv_values(env_path)

print("--- Diagnostic ---")
print("Clés trouvées dans le fichier .env :", list(config.keys()))
if "DATABASE_URL" in config:
    print("DATABASE_URL est bien présent dans le fichier.")
else:
    print("ERREUR : DATABASE_URL n'a pas été trouvé dans le fichier .env")
    # Affiche le contenu brut pour voir s'il y a un problème de lecture
    with open(env_path, 'r') as f:
        print("Contenu brut du fichier :\n", f.read())
