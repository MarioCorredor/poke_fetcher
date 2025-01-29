import requests
from pymongo import MongoClient

# Conectar a MongoDB
username = 'pokemon_db'
password = 'H6fdOF2505Qn3boQ'

uri = f'mongodb+srv://{username}:{password}@clusterpoke.hexkh.mongodb.net/?retryWrites=true&w=majority&appName=ClusterPoke'

client = MongoClient(uri)

db = client['pokemon_db']
pokemon_collection = db['pokemon']
evolution_collection = db['evolution_chain']

# URL base de la PokeAPI
base_url = "https://pokeapi.co/api/v2/"

def get_pokemon_data(pokemon_id):
    response = requests.get(f"{base_url}pokemon/{pokemon_id}")
    if response.status_code == 200:
        pokemon_data = response.json()

        # Obtener URL de species
        species_url = pokemon_data.get('species', {}).get('url')
        species_data = {}

        if species_url:
            species_response = requests.get(species_url)
            if species_response.status_code == 200:
                species_data = species_response.json()
            else:
                print(f"Error al obtener datos de species para Pokémon ID {pokemon_id}: {species_response.status_code}")

        # Obtener ID de la cadena de evolución
        evolution_chain_url = safe_get(species_data, ['evolution_chain', 'url'], None)
        evolution_chain_id = int(evolution_chain_url.split('/')[-2]) if evolution_chain_url else None

        # Preparar datos del Pokémon
        pokemon_info = {
            "id": pokemon_data.get('id'),
            "name": pokemon_data.get('name'),
            "weight": pokemon_data.get('weight'),
            "height": pokemon_data.get('height'),
            "stats": {stat['stat']['name']: stat['base_stat'] for stat in pokemon_data.get('stats', [])},
            "abilities": [ability['ability']['name'] for ability in pokemon_data.get('abilities', [])],
            "types": [type['type']['name'] for type in pokemon_data.get('types', [])],
            "sprites": {
                "front_default": safe_get(pokemon_data, ['sprites', 'front_default'], None),
                "front_shiny": safe_get(pokemon_data, ['sprites', 'front_shiny'], None)
            },
            "capture_rate": safe_get(species_data, ['capture_rate']),
            "main_color": safe_get(species_data, ['color', 'name']),
            "habitat": safe_get(species_data, ['habitat', 'name']),
            "generation": safe_get(species_data, ['generation', 'name']),
            "evolution_chain_id": evolution_chain_id
        }
        return pokemon_info, evolution_chain_url
    else:
        print(f"Error al obtener datos de Pokémon ID {pokemon_id}: {response.status_code}")
        return None, None


def get_evolution_chain(evolution_chain_url):
    response = requests.get(evolution_chain_url)
    if response.status_code == 200:
        evolution_data = response.json()
        chain = evolution_data.get('chain', {})
        evolution_chain = parse_evolution_chain(chain)
        return evolution_chain
    else:
        return None

def parse_evolution_chain(chain):
    species = chain.get('species', {}).get('name')
    evolution_details = [{
        "trigger": detail.get('trigger', {}).get('name') if detail.get('trigger') else None,
    } for detail in chain.get('evolution_details', [])]
    
    evolves_to = [parse_evolution_chain(evo) for evo in chain.get('evolves_to', [])]
    return {
        "species": species,
        "evolution_details": evolution_details,
        "evolves_to": evolves_to
    }

def safe_get(d, keys, default="None"):
    """
    Accede de forma segura a claves anidadas en un diccionario.
    Si cualquier clave no existe o el valor es None, devuelve el valor por defecto.
    """
    for key in keys:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            return default
    return d if d is not None else default

def fetch_all_pokemon():
    pokemon_id = 1
    while True:
        # Verificar si el Pokémon ya existe en la base de datos
        if pokemon_collection.find_one({"id": pokemon_id}):
            print(f"Pokémon {pokemon_id} ya existe en la base de datos. Pasando al siguiente.")
            pokemon_id += 1
            continue

        # Obtener datos del Pokémon
        pokemon_data, evolution_chain_url = get_pokemon_data(pokemon_id)
        if not pokemon_data:
            print(f"No se encontraron más datos para Pokémon ID {pokemon_id}. Finalizando.")
            break

        # Insertar Pokémon en la colección si no existe
        pokemon_collection.insert_one(pokemon_data)
        print(f"Pokémon {pokemon_id} insertado en la base de datos.")

        # Obtener y almacenar la cadena de evolución si no existe
        if evolution_chain_url:
            try:
                # Intentar calcular el ID de la cadena de evolución
                evolution_chain_id = int(evolution_chain_url.split('/')[-2])
            except (ValueError, IndexError):
                print(f"Error al obtener el ID de la cadena de evolución para Pokémon ID {pokemon_id}.")
                evolution_chain_id = None

            if evolution_chain_id:
                # Verificar si la cadena de evolución ya existe en la base de datos
                if not evolution_collection.find_one({"id": evolution_chain_id}):
                    evolution_chain = get_evolution_chain(evolution_chain_url)
                    if evolution_chain:
                        evolution_collection.insert_one({
                            "id": evolution_chain_id,
                            "chain": evolution_chain
                        })
                        print(f"Cadena de evolución {evolution_chain_id} insertada en la base de datos.")
                    else:
                        print(f"No se pudo obtener la cadena de evolución para ID {evolution_chain_id}.")
                else:
                    print(f"Cadena de evolución {evolution_chain_id} ya existe en la base de datos.")

        pokemon_id += 1

if __name__ == "__main__":
    fetch_all_pokemon()
