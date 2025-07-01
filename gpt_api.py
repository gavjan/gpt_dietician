from openai import OpenAI
import ast
import json

# OpenAI API KEY
with open(".env/openai.key", "r") as f:
    API_KEY = f.read().strip()
client = OpenAI(api_key=API_KEY)

query_struct = {
    "title": "<str> title of the meal option",
    "ingredients": "<str> ingridients approximation given by the catering",
    "allergens": "<str> use this if the user specified any allergies",
    "nutritional_value": "<str> approximate nutritional value given by the catering"
}

sample_query = [
    {
        "title": "Zestaw śniadaniowy: chleb proteinowy, twarożek ze szczypiorkiem, wędzony łosoś, ogórek",
        "ingredients": "chleb proteinowy 32% (woda, białka roślinne (PSZENNE, SOJOWE, ŁUBINOWE), produkty przemiału SOI (śruta, płatki), siemię lniane, ziarno słonecznika, mąka PSZENNA graham, drożdże, kwas PSZENNY w proszku, sól, słód JĘCZMIENNY, błonnik OWSIANY), ogórek zielony 26%, łosoś wędzony na zimno 22% (ŁOSOŚ atlantycki, sól), ser 20% (SER twarogowy półtłusty, ser śmietankowy (MLEKO pasteryzowane, ŚMIETANKA), szczypiorek, sól, pieprz czarny)",
        "allergens": "gluten, mleko, ryby i produkty pochodne, soja, łubin",
        "nutritional_value": "Wartość odżywcza w porcji XL. Wartość energetyczna: 2600 kJ / 622 kcal. Tłuszcz: 37,7 g. W tym kwasy tł. nasycone: 9,9 g. Węglowodany: 9,7 g. W tym cukry: 3,1 g. Błonnik: 19,8 g. Białko: 56,9 g. Sól: 5,5 g."
    },
    {
        "title": "Omlet twarogowy z malinami, jogurt grecki, konfitura porzeczkowa z chia",
        "ingredients": "omlet 57% (SER twarogowy półtłusty, JAJA kurze, maliny, mąka ziemniaczana, ksylitol), jogurt grecki 29% (ŚMIETANKA, MLEKO w proszku, białka MLEKA, żywe kultury bakterii jogurtowych), konfitura 14% (porzeczki czarne, ksylitol, nasiona chia, woda, mąka ziemniaczana)",
        "allergens": "jaja, mleko",
        "nutritional_value": "Wartość odżywcza w porcji XL. Wartość energetyczna: 2416 kJ / 578 kcal. Tłuszcz: 27,3 g. W tym kwasy tł. nasycone: 15,4 g. Węglowodany: 63,6 g. W tym cukry: 17,6 g. Błonnik: 9,1 g. Białko: 33,8 g. Sól: 0,6 g."
    },
    {
        "title": "Proteinowe pancakes, wysokobiałkowy krem migdałowy, brzoskwinia, borówki",
        "ingredients": "pancake 50% (skyr (MLEKO, żywe kultury bakterii jogurtowych: Streptococcus thermophilus i Lactobacillus bulgaricus), mąka ORKISZOWA, JAJA kurze, ksylitol, olej rzepakowy, ksylitol waniliowy (Ksylitol, wanilia naturalna mielona), soda oczyszczona, proszek do pieczenia, sól), krem 17% (pasta z migdałów (MIGDAŁY pieczone), napój migdałowy (Woda, MIGDAŁ, ekstrakt z MIGDAŁÓW, stabilizator: (ekologiczna mączka chleba świętojańskiego), sól morska), odżywka białkowa biała czekolada (Koncentrat białka serwatki (z MLEKA), stabilizator: guma arabska, regulator kwasowości: kwas jabłkowy, aromat, substancja słodząca: sukraloza), ksylitol, woda mineralna niegazowana), borówka amerykańska 17%, brzoskwinia 17%",
        "allergens": "gluten, jaja, mleko, orzechy",
        "nutritional_value": "Wartość odżywcza w porcji XL. Wartość energetyczna: 2399 kJ / 574 kcal. Tłuszcz: 24,2 g. W tym kwasy tł. nasycone: 3 g. Węglowodany: 63 g. W tym cukry: 9,2 g. Błonnik: 7,6 g. Białko: 33,8 g. Sól: 0,7 g."
    }
]
response_struct = {
    "picked_option": "<uint> your chosen food's number (from 0) based on how many food options are in the query",
    "protein": "<float> numebr in grams, query should include protein from `nutritional_value`, find protein count and include it in here. If it's missing, try to estimate",
    "creatine": "<float> number in grams, estimate creatine only if the ingredient is meat/fish (e.g., beef, salmon). Otherwise, use 0.",
    "omega3": "<float> number in grams, exaxct amount won't be in the query, try to estimate based on the info you get",
    "comments": "<str> If you have any comments, put them here. But keep them very short. You may leave it empty"
}
sample_response = {
    "picked_option": 0,
    "protein": 56.4,
    "creatine": 0.51,
    "omega3": 0,
    "comments": ""
}
error_response = {
    "picked_option": 0,
    "protein": 0,
    "creatine": 0,
    "omega3": 0,
    "comments": "GPT is trolling"
}

CLIENT = {
    "name": "Gav",
    "weight": "62kg",
    "sex": "Male",
    "food_preference": "Healthy gym diet for bulking naturally with 5-days a week workout. Consider protein and creatine count, but prioritise my preferences. No pickles, no overly-spicy stuff, I like fish, Lasagna always wins." 
}
SYSTEM_MSG =f'''
You're {CLIENT['name']}'s personal Nutritionist.
Here's his basic info: {CLIENT}.
An automated bot will send you a list of JSON objects with the following structure: {query_struct}.
Always respond back with a JSON object that has the following structure: {response_struct}.
Your responses will be processed by the bot. Therefore, it should always be a JSON matching the above-mentioned rules.
If you have any comments, put them in the comments field of the JSON.
Don't respond with anything other than the JSON.
Here's an example of how your response could look like: {sample_response} 
Do NOT wrap the JSON in markdown code blocks or backticks, follow the same styling as the example.
'''

def ask_gpt(meal_options):
    def ask_api(content):
        response = client.chat.completions.create(model="gpt-4o", temperature=0, messages=[
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": f'{content}'}
        ])
        return response.choices[0].message.content
    
    response_text = ask_api(meal_options)
    try:
        return ast.literal_eval(response_text)
    except (SyntaxError, ValueError) as e:
        try:
            return ast.literal_eval(response_text)
        except (SyntaxError, ValueError) as e:  
            pass
    return error_response

def pick_meal(meal_options):
    resp = ask_gpt(meal_options)
    print(json.dumps(resp, indent=4, ensure_ascii=False))
    return resp

def main():
    resp_json = ask_gpt(sample_query)
    print(json.dumps(resp_json, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    exit(main())
