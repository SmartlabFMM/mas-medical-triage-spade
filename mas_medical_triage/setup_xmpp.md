# Configuration serveur XMPP pour SPADE

## Option 1 — Docker (recommandé, le plus simple)

```bash
docker run -d \
  --name prosody \
  -p 5222:5222 \
  -p 5280:5280 \
  -e LOCAL_DOMAIN=localhost \
  prosody/prosody
```

Puis crée les 4 comptes agents :
```bash
docker exec -it prosody prosodyctl register conversational localhost conv123
docker exec -it prosody prosodyctl register clinical localhost clin123
docker exec -it prosody prosodyctl register resource localhost res123
docker exec -it prosody prosodyctl register meta localhost meta123
```

## Option 2 — Sans Docker (Windows)

1. Télécharge Prosody : https://prosody.im/download/start
2. Installe-le et démarre le service
3. Dans le terminal Prosody :
```
prosodyctl register conversational localhost conv123
prosodyctl register clinical localhost clin123
prosodyctl register resource localhost res123
prosodyctl register meta localhost meta123
```

## Option 3 — Serveur public (test uniquement)

Modifie le .env avec un serveur public gratuit :
```
XMPP_SERVER=jabber.fr
JID_CONVERSATIONAL=tonnom_conv@jabber.fr
...
```
Crée les comptes sur https://jabber.fr

## Lancement après configuration

```bash
pip install -r requirements.txt
python main.py
```
