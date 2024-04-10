from flask import Flask, request, jsonify
import requests
import logging
import json

app = Flask(__name__)

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
    user_id = req['session']['user_id']

    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови свое имя и кодовое слово!'
        sessionStorage[user_id] = {
            'first_name': None,
            'key_word': None,
            'game_started': False
        }
        return

    if sessionStorage[user_id]['first_name'] is None:
        key_word = None
        if len(req.split()) == 2:
            key_word = req.split()[1]
            first_name = get_first_name(req)
        else:
            res['response']['text'] = 'Необходимо указать 2 слова'

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
                res['response']['text'] = 'Хорошо, угадай первый город'
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
            game(res, req)


def game(res, req):
    pass


def get_first_name(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.FIO':
            return entity['value'].get('first_name', None)


if __name__ == '__main__':
    app.run()
