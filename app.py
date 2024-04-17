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
pictures = {'1': None,
            '2': None,
            '3': None}
for picture in db_sess.query(Picture).all():
    if picture[5] == 1:
        pictures['1'][picture[1]] = [picture[3], picture[4]]
        pictures['1'][picture[1]]['key'] = [picture[2]]
        pictures['1'][picture[1]]['name'] = [picture[1]]
    elif picture[5] == 2:
        pictures['2'][picture[1]] = [picture[3], picture[4]]
        pictures['2'][picture[1]]['key'] = [picture[2]]
    elif picture[5] == 3:
        pictures['3'][picture[1]] = [picture[3], picture[4]]
        pictures['3'][picture[1]]['key'] = [picture[2]]

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
            'level': None,
            'objects': [],
            'score': 0
        }
        return
    if sessionStorage[user_id]['first_name'] is None:
        print('ok')
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
                sessionStorage[user_id]['level'] = 1
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
            if req['request']['nlu']['tokens'].lower() == name_pict:
                sessionStorage[user_id]['objects'].append(name_pict)
                sessionStorage[user_id]['score'] += 1
                res['response']['text'] = 'Вы угадали! Хотите продолжить игру?'
                name_pict = None
                return
            else:
                res['response']['text'] = f'К сожалению, вы не угадали это {name_pict}. Хотите продолжить игру?'
                name_pict = None
                sessionStorage[user_id]['objects'].append(name_pict)
                return
            if 'да' in req['request']['nlu']['tokens']:
                game(res, req)
                return
            else:
                res['response']['text'] = f'Хорошо, приятно было с вами сыграть. Ваш счёт ' \
                                          f'{sessionStorage[user_id]["score"]}'
                return


def geocode(lat, long):
    url = 'https://static-maps.yandex.ru/v1'
    map_request = f'http://static-maps.yandex.ru/1.x/?ll={lat},{long}&spn=30,30&l=sat'
    response = requests.get(map_request)

    if not response:
        print("Ошибка выполнения запроса:")
        print(map_request)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        sys.exit(1)
    map_file = "img/map.png"
    with open(map_file, "wb") as file:
        file.write(response.content)


def game(res, req):
    global name_pict
    user_id = req['session']['user_id']
    if len(sessionStorage[user_id]['objects']) == len(pictures[sessionStorage[user_id]['level']]):
        sessionStorage[user_id]['level'] += 1
        sessionStorage[user_id]['objects'] = []
        if sessionStorage[user_id]['level'] > len(pictures):
            res['response'][
                'text'] = f'Вы прошли игру, ваш счёт {sessionStorage[user_id]["score"]}.' \
                          f' Хотите добавить свои данные к нам в базу?'
            if 'да' in req['request']['nlu']['tokens']:
                res['response']['text'] = 'Хорошо, вам нужно отправить название объекта, его долготу и широту'
                if len(req['request']['original_utterance'].split()) == 3:
                    name = req['request']['original_utterance'].split()[0]
                    lat = req['request']['original_utterance'].split()[1]
                    long = req['request']['original_utterance'].split()[3]
                    picture.name = name
                    picture.long = long
                    picture.lat = lat
                    db_sess.add(picture)
                    geocode(lat, long)
                else:
                    res['response']['text'] = 'Необходимо указать 3 слова'
                    return
            else:
                res['response']['text'] = f'Хорошо, приятно было с вами сыграть.'
                return
    key_pict = random.choice(pictures[sessionStorage[user_id]['level']]['key'])
    while name_pict in sessionStorage[user_id]['objects']:
        key_pict = random.choice(pictures[sessionStorage[user_id]['level']]['key'])
    name_pict = pictures['1'][picture[1]]['name']
    res['response']['card'] = {}
    res['response']['card']['type'] = 'BigImage'
    res['response']['card']['title'] = 'Угадай, что это за объект'
    res['response']['card']['image_id'] = key_pict


# TODO ПОДУМАТЬ над переносом в верхнюю функцию
# увелечиние уровню сложности относительно количества указанных картинок или завершение игры


def get_first_name(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.FIO':
            return entity['value'].get('first_name', None)


if __name__ == '__main__':
    app.run()
