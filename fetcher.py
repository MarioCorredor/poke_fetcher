import requests
from pymongo import MongoClient
import re

# Conectar a MongoDB
username = 'pokemon_db'
password = 'H6fdOF2505Qn3boQ'

uri = f'mongodb+srv://{username}:{password}@clusterpoke.hexkh.mongodb.net/?retryWrites=true&w=majority&appName=ClusterPoke'

client = MongoClient(uri)
db = client['pokemon_db']
pokemon_collection = db['pokemon']

# URL base de la PokeAPI
base_url = "https://pokeapi.co/api/v2/"

def get_pokemon_data(pokemon_id):
    response = requests.get(f"{base_url}pokemon/{pokemon_id}")
    if response.status_code == 200:
        pokemon_data = response.json()
        
        species_url = pokemon_data.get('species', {}).get('url')
        species_data = {}
        evolution_chain = {}
        
        if species_url:
            species_response = requests.get(species_url)
            if species_response.status_code == 200:
                species_data = species_response.json()
                evolution_chain_url = species_data.get('evolution_chain', {}).get('url')
                
                if evolution_chain_url:
                    evolution_response = requests.get(evolution_chain_url)
                    if evolution_response.status_code == 200:
                        evolution_chain = evolution_response.json()
        
        evolution_stage, evolution_trigger = determine_evolution_stage_and_trigger(evolution_chain, pokemon_data.get('name'))
        
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
            "cries": {"latest": safe_get(pokemon_data, ['cries', 'latest'], None)},
            "capture_rate": safe_get(species_data, ['capture_rate']),
            "main_color": safe_get(species_data, ['color', 'name']),
            "habitat": safe_get(species_data, ['habitat', 'name']),
            "generation": safe_get(species_data, ['generation', 'name']),
            "evolution_stage": evolution_stage,
            "evolution_trigger": evolution_trigger if evolution_trigger else "None"
        }
        return pokemon_info
    else:
        print(f"Error al obtener datos de Pokémon ID {pokemon_id}: {response.status_code}")
        return None

def determine_evolution_stage_and_trigger(evolution_chain, pokemon_name, stage=1, trigger="None"):
    if not evolution_chain or 'chain' not in evolution_chain:
        return 1, "None"
    
    # Si el nombre tiene un "-", usamos solo la primera parte
    base_name = re.split(r'-', pokemon_name)[0]
    
    chain = evolution_chain['chain']
    return find_stage_and_trigger(chain, base_name, stage, trigger)

def find_stage_and_trigger(chain, pokemon_name, stage, trigger):
    if chain['species']['name'] == pokemon_name:
        return stage, trigger
    for evo in chain['evolves_to']:
        for detail in evo['evolution_details']:
            next_trigger = detail.get('trigger', {}).get('name', "None")
            next_stage, final_trigger = find_stage_and_trigger(evo, pokemon_name, stage + 1, next_trigger)
            if next_stage:
                return next_stage, final_trigger
    return None, "None"

def safe_get(d, keys, default="None"):
    for key in keys:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            return default
    return d if d is not None else default

def fetch_all_pokemon():
    for pokemon_id in list(range(1, 1026)) + list(range(10001, 10280)):
        if pokemon_collection.find_one({"id": pokemon_id}):
            print(f"Pokémon {pokemon_id} ya existe en la base de datos. Pasando al siguiente.")
            continue
        pokemon_data = get_pokemon_data(pokemon_id)
        if not pokemon_data:
            print(f"No se encontraron más datos para Pokémon ID {pokemon_id}.")
            continue
        pokemon_collection.insert_one(pokemon_data)
        print(f"Pokémon {pokemon_id} insertado en la base de datos.")

if __name__ == "__main__":
    fetch_all_pokemon()
