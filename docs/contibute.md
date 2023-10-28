# Comment executer le bot en local ?

## I. En utilisant Docker

### 1. Qu'est-ce que Docker ?

Docker est un outil de pour gérer des conteneurs. Pour faire très simple : un conteneur, c'est comme une machine virtuelle, mais vous ne virtualisez que le software, pas l'hardware. C'est donc assez léger, et ça permet surtout d'avoir les **même conditions d'execution** peu importe l'ordinateur que vous utilisez, sans **soucis de compatibilité**, et ça évite aussi d'avoir à installer des choses sur son ordinateur (python, libraires C, base de données...) : dès que vous supprimez le conteneur, il n'y a plus de trace sur votre ordinateur !

### 2. Installer Docker

Il y a "2" versions de Docker : la version serveur et la version Desktop. Sur Windows et MacOS, seule la version Desktop est disponible. Elle fournit une interface graphique qui sera facile à prendre en main.

Sous Windows et MacOS, Docker est un peu moins optimisé que sous Linux, car une "surcouche" va se rajouter pour simuler Linux (une petite VM), mais c'est pas important : simplement, pensez à fermer docker quand vous ne l'utilisez pas pour vous économiser un peu de batterie.

Pour l'installer, c'est ici : https://docs.docker.com/engine/install/

Pour vérifier votre installation, ouvrez un terminal et faites :

```
sudo docker run hello-world
```

Vérifiez bien aussi que `docker-compose` est installé aussi, tapant la commande `docker compose` ou `docker-compose`. Sinon, regardez comment l'installer.

### 3. Executer le bot

Assurez-vous d'avoir suivi les [prérequis](#iii-configurez-le-projet) avant d'aller plus loin.

Allez à la source du projet : le même répertoire que le dossier `src/` ou que le fichier `docker-compose.yml`.

#### A. Version production

Tapez dans le terminal la commande :

```
docker compose up --build
```

Cette commande est un tout-en-un : sans entrer dans le fonctionnement de Docker, cette commande va :

- construire une image du projet avec des paramètres prédéfinis par le fichier `docker-compose.yml` en se basant sur le fichier `Dockerfile`.
- executer cette image dans un conteneur, en faisant les associations éventuel avec d'autres conteneurs.

Pour arrêtez le bot, vous pouvez simplement faire `CTRL-C` dans la console. Cette opération peu prendre quelques secondes.

Pour tout supprimer, le plus simple est de le faire depuis l'interface graphique avec Docker Desktop.

#### B. Version debug

Si vous utilisez VSCode, vous pouvez utilisez debugpy pour avoir un réel debugger.

Créez un fichier `.vscode/tasks.json`, et collez le json suivant :

```json
{
  // See https://go.microsoft.com/fwlink/?LinkId=733558
  // for the documentation about the tasks.json format
  "version": "2.0.0",
  "tasks": [
    {
      "label": "run debug",
      "type": "shell",
      "command": "docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build --force-recreate -d",
      "presentation": {
        "echo": true,
        "reveal": "silent",
        "focus": false,
        "panel": "shared",
        "showReuseMessage": false,
        "clear": false
      },
      "problemMatcher": []
    },
    {
      "label": "run prod",
      "type": "shell",
      "command": "docker-compose -f docker-compose.yml up --build -d",
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "new",
        "showReuseMessage": true,
        "clear": false
      },
      "problemMatcher": []
    },
    {
      "label": "stop bot",
      "type": "shell",
      "command": "docker-compose stop",
      "presentation": {
        "echo": true,
        "reveal": "silent",
        "focus": false,
        "panel": "shared",
        "showReuseMessage": false,
        "clear": false
      },
      "problemMatcher": []
    }
  ]
}
```

Créez un fichier `.vscode/launch.json` et collez le json suivant :

```json
{
  // Use IntelliSense to learn about possible attributes.
  // Hover to view descriptions of existing attributes.
  // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Remote Attach",
      "type": "python",
      "request": "attach",
      "preLaunchTask": "run debug",
      // "postDebugTask": "stop bot",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}/src",
          "remoteRoot": "/app"
        }
      ]
    }
  ]
}
```

Depuis l'onglet `debug`, vous pouvez maintenant sélectionner "Python : Remote Attach" et cliquer sur `play`. Le debugger s'ouvre, vous permettant de mettre des break points, etc...
_Il faut parfois cliquer plusieurs fois sur le `play`._

Cette version de débogage vous permet aussi d'activer l'extension `admin` et d'utiliser la commande `/reload_extension` pour recharger dynamiquement des extensions sans avoir à redémarrer le bot. Changez simplement les fichiers et rechargez l'extension.

## II. En utilisant une installation Python classique

Suivez les [prérequis](#iii-configurez-le-projet) avant de continuer.

Allez à la racine du projet, c'est-à-dire dans le répertoire où se trouve le dossier `src/` ou le fichier `requirements.txt`.

### Créez un environnement virtuel

Exécutez la commande suivante :

```
python -m venv venv
```

_Si vous êtes sur Linux, il faut peut être faire `python3`, si vous êtes sur Windows, il faut peut être faire `py`._

Activez vous environnement :

- Sur MacOS et Linux :

```
source venv/bin/activate
```

- Sur Windows :

```
venv/bin/activate.ps1
```

Installez les paquets :

```
pip install -r requirements.txt
pip install python-dotenv
```

### Exécutez le bot

Il n'y a plus qu'à lancer le bot depuis le fichier `/src/main.py` :

```
python3 ./src/main.py
```

## III. Configurez le projet

### 1. Créez vous votre propre bot

Sur le site https://discord.dev, créez une application, puis un bot. Copiez le token, et invitez le bot sur l'un de vos serveur, dédié aux tests.

### 2. Définissez les variables d'environnement

Créez un fichier `.env` de la forme :

```.env
VARIABLE=VALEUR
```

Les variables possibles sont :

- `BOT_TOKEN` (requise)
- `CTS_TOKEN` (pour l'extension `cts` seulement)
- `OPENWEATHERMAP_API_KEY` (pour l'extension `weather_icon` seulement)
- `OPENAI_API_KEY` (pour l'extension `openia_chatbot` seulement)

### 3. Changez les constantes et extensions chargées

Modifiez le fichier `/src/core/constants.py` selon vos propres paramètres. Vous devrez donc sûrement changer les variables suivantes : `GUILD_ID`, `MAIN_CHANNEL_ID`.

Si vous travaillez sur une fonctionnalité du bot, désactivez les autres! Surtout s'il vous manque des tokens, etc...
Modifiez donc la variable `LOADED_EXTENSIONS`.
Une extension est un fichier situé directement dans `/src/cogs/`. Ça peut aussi être un dossier avec un fichier `__init__.py`, du moment que ça peut être importé. Plus d'information dans les informations sur [la structure du bot](/docs/bot-structure.md).
