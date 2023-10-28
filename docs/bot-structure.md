# La structure du projet

## Les fichiers à la racine

- `requirements.txt` : contient les dépendances du bot, c'est-à-dire les paquets à installer pour faire fonctionner le bot.
- `requirements.dev.txt` : contient les dépendances optionnelles du bot, c'est-à-dire tout ce qui touche au style, les linters, les outils de mise en forme du code...
- `pyproject.toml` : contient des paramètres et des configuration pour les outils cités ci-dessus.
- `Dockerfile` : contient les instructions utilisées par Docker pour construire l'image du bot.
- `docker-compose.yml` : "permet d'utiliser plus facilement Docker".
- `docker-compose.dev.yml` : pour executer la version debug sous Docker.
- `.gitignore` : liste les fichiers ignorés par Git : ils ne seront pas ajouté sur github.com.
- `.dockerignore` : liste les fichiers ignorés par Docker : ils ne seront pas ajouté dans l'image.

## Les dossiers à la racine

- `data/` : contient les informations modifiées dynamiquement par le bot. Typiquement, les données de la base de donnée.
- `docs/` : contient des divers explications.
- `readme-images/` : contient des images utilisées dans le readme.
- `resources/` : contient des informations statiques utilisées par le bot.
- `src/` : contient le code source du bot.
- `/typings` : contient des informations de typage pour certaines dépendances qui n'en ont pas.

## Le dossier `src/`

### `src/librairies`

Ce répertoire contient des librairies très simples créées pour simplifier l'utilisation d'API.

### `src/core`

Contient tout le code du bot qui peut servir à plus d'une fonctionnalité du bot. C'est le cœur du bot.

### `src/cogs`

Ce sont les extensions du bot. Si vous n'êtes pas habitué à `Discord.py`, voici une explication très simple :

Depuis [`bot.py`](/src/bot.py), on va charger les extensions avec la fonction [`commands.Bot.load_extension()`](https://discordpy.readthedocs.io/en/latest/ext/commands/api.html?highlight=load_extension#discord.ext.commands.Bot.load_extension). Cette fonction va importer le fichier donné en argument (par exemple, `cogs.cts` va importer `/src/cogs/cts.py`), et chercher une fonction `setup()` dans ce fichier, en donnant le bot en argument.

Cette fonction pourrait ressembler un peu à ça :

```python
class Bot:
    async def load_extension(self, path: str):
        ext = importlib.import_module(path)
        await ext.setup(self)
```

Depuis cette fonction, l'extension "s'auto ajoute" avec la fonction [`commands.Bot.add_cog()`](https://discordpy.readthedocs.io/en/latest/ext/commands/api.html?highlight=add_cog#discord.ext.commands.Bot.add_cog)

Voici un exemple très simple d'extension, pour illustrer :

```python
from discord import app_commands
from discord.ext import commands
import discord

class HelloWorld(commands.Cog):
    @app_commands.command()
    async def hello_world(self, inter: discord.Interaction):
        await inter.response.send_message("Hello World !")

async def setup(bot):
    await bot.add_cog(HelloWorld())
```

Points notables :

- au moment de l'initialisation du `Cog` (dans le `__init__()`), le cache n'est pas construit. Ainsi toutes fonctions `get` (`bot.get_guild`, `bot.get_channel`) renverra `None`
- vous pouvez définir une fonction `cog_load` qui sera appelée au moment de charger le cog. Son premier avantage est que si vous rechargez l'extension, les données seront actualisées. Son second avantage est que cette fonction est asynchrone, contrairement au `__init__`. Néanmoins, n'attendez pas que le bot soit "prêt" dans cette fonction, parce que le bot attend la fin de cette fonction pour se déclarer prêt.
- de la même manière, vous pouvez définir une fonction `cog_unload`.
