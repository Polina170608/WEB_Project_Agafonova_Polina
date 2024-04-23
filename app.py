import sys
import random
from flask import Flask, request, jsonify
import requests
import logging
from data import db_session
from data.picture import Picture

app = Flask(__name__)

db_session.global_init("db/users.db")
db_sess = db_session.create_session()
name_pict = None
pictures = {'1': [],
            '2': [],
            '3': []}
for picture in db_sess.query(Picture).all():
    if picture.level == 1:
        pictures['1'].append({'lon': picture.long, 'lat': picture.lat,
                              'key': picture.key, 'name': picture.name})
    elif picture.level == 2:
        pictures['2'].append({'lon': picture.long, 'lat': picture.lat,
                              'key': picture.key, 'name': picture.name})
    elif picture.level == 3:
        pictures['3'].append({'lon': picture.long, 'lat': picture.lat,
                              'key': picture.key, 'name': picture.name})

logging.basicConfig(level=logging.INFO)

sessionStorage = {}


@app.route('/post', methods=['POST'])
def main():
    logging.info(f'Request: {request.json!r}')
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info(f'Response: {response!r}')
    return jsonify(response)


def handle_dialog(res, req):
    global name_pict
    user_id = req['session']['user_id']
    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови свое имя и кодовое слово!'
        sessionStorage[user_id] = {
            'first_name': None,
            'key_word': None,
            'game_started': False,
            'level': '1',
            'objects': [],
            'score': 0,
            'add_object': False
        }
        return
    if sessionStorage[user_id]['first_name'] is None:
        key_word = None
        first_name = None
        if len(req['request']['original_utterance'].split()) == 2:
            key_word = req['request']['original_utterance'].split()[1]
            first_name = get_first_name(req)
        else:
            res['response']['text'] = 'Необходимо указать 2 слова'
            return

        if first_name is None:
            res['response']['text'] = \
                'Не расслышала имя. Повтори, пожалуйста!'
        elif key_word is None:
            res['response']['text'] = \
                'Не расслышала кодовое слово. Повтори, пожалуйста!'
        else:
            sessionStorage[user_id]['first_name'] = first_name
            sessionStorage[user_id]['key_word'] = key_word
            res['response'][
                'text'] = 'Приятно познакомиться, ' \
                          + first_name.title() \
                          + '. Хочешь сыграть в игру "Угадай географический объект"?'

            res['response']['buttons'] = [
                {
                    'title': 'да',
                    'hide': True
                },
                {
                    'title': 'нет',
                    'hide': True
                }
            ]
    else:
        if not sessionStorage[user_id]['game_started']:
            if 'да' in req['request']['nlu']['tokens']:
                sessionStorage[user_id]['game_started'] = True
                sessionStorage[user_id]['level'] = '1'
                res['response']['text'] = 'Хорошо, угадай первый объект'
                game(res, req)
            elif 'нет' in req['request']['nlu']['tokens']:
                res['response']['text'] = 'Хорошо, увидимся позже'
                res['end_session'] = True
            else:
                res['response']['text'] = 'Я не поняла.Будем играть?'
                res['response']['buttons'] = [
                    {
                        'title': 'да',
                        'hide': True
                    },
                    {
                        'title': 'нет',
                        'hide': True
                    }
                ]
        else:
            if name_pict:
                if name_pict.lower() in req['request']['original_utterance'].lower():
                    sessionStorage[user_id]['objects'].append(name_pict)
                    sessionStorage[user_id]['score'] += 1
                    res['response']['text'] = 'Вы угадали! Хотите продолжить игру?'
                    name_pict = None
                    return
                else:
                    res['response']['text'] = f'К сожалению, вы не угадали. Это {name_pict}. Хотите продолжить игру?'
                    name_pict = None
                    sessionStorage[user_id]['objects'].append(name_pict)
                    return
            else:
                if ('да' in req['request']['original_utterance']) and int(sessionStorage[user_id]['level']) < 4:
                    res['response']['text'] = 'Итак, мы продолжаем'
                    game(res, req)
                    return
                elif ('да' in req['request']['original_utterance']) and int(sessionStorage[user_id]['level']) > 3:
                    sessionStorage[user_id]['add_object'] = True
                    res['response'][
                        'text'] = 'Хорошо, вам нужно отправить название объекта (вместо пробела используй _ ), ' \
                                  'его долготу и широту (без запятых), ' \
                                  'а также предполагаемый уровень сложности (1, 2, 3)'
                    return
                elif sessionStorage[user_id]['add_object']:
                    if len(req['request']['original_utterance'].split()) == 4:
                        name = ' '.join(req['request']['original_utterance'].split('_')[0])
                        lat = req['request']['original_utterance'].split()[1]
                        long = req['request']['original_utterance'].split()[2]
                        level = req['request']['original_utterance'].split()[3]
                        pict = Picture()
                        pict.name = name
                        pict.long = long
                        pict.lat = lat
                        pict.level = level
                        db_sess = db_session.create_session()
                        db_sess.add(pict)
                        db_sess.commit()
                        geocode(lat, long, user_id)
                        res['response']['text'] = f'Хорошо, приятно было с вами сыграть. Ваш счёт ' \
                                                  f'{sessionStorage[user_id]["score"]}'
                        return
                    else:
                        res['response']['text'] = 'Необходимо указать 4 слова'
                        return
                else:
                    res['response']['text'] = f'Хорошо, приятно было с вами сыграть. Ваш счёт ' \
                                              f'{sessionStorage[user_id]["score"]}'
                    return


def geocode(lat, long, user_id):
    map_request = f'http://static-maps.yandex.ru/1.x/?ll={lat},{long}&0.05,0.05&l=sat'
    response = requests.get(map_request)
    if not response:
        print("Ошибка выполнения запроса:")
        print(map_request)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        sys.exit(1)
    map_file = f"img/map{user_id}.png"
    with open(map_file, "wb") as file:
        file.write(response.content)


def game(res, req):
    global name_pict
    user_id = req['session']['user_id']
    if len(sessionStorage[user_id]['objects']) == len(pictures[sessionStorage[user_id]['level']]):
        sessionStorage[user_id]['level'] = str(int(sessionStorage[user_id]['level']) + 1)
        sessionStorage[user_id]['objects'] = []
        if int(sessionStorage[user_id]['level']) > len(pictures):
            res['response']['text'] = f'Вы прошли игру. Хотите добавить свои данные к нам в базу?'
            return
        res['response']['text'] = f'Вы угадали все объекты данного уровня, поэтому переходите на следующий. ' \
                                  f'Ваш счёт {sessionStorage[user_id]["score"]}.'
    key_pict = random.choice(pictures[str(sessionStorage[user_id]['level'])])
    name_pict = key_pict['name']
    while name_pict in sessionStorage[user_id]['objects']:
        key_pict = random.choice(pictures[str(sessionStorage[user_id]['level'])])
        name_pict = key_pict['name']
    key_pict = key_pict['key']
    print(name_pict)
    res['response']['card'] = {}
    res['response']['card']['type'] = 'BigImage'
    res['response']['card']['title'] = 'Угадай, что это за объект'
    res['response']['card']['image_id'] = key_pict


def get_first_name(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.FIO':
            return entity['value'].get('first_name', None)


if __name__ == '__main__':
    app.run()
