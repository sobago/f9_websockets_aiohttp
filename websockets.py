import datetime
import json
import logging
import os
from aiohttp import web

WS_FILE = os.path.join(os.path.dirname(__file__), 'index.html')


async def wshandler(request: web.Request):
    response = web.WebSocketResponse()
    available = response.can_prepare(request)
    if not available:
        with open(WS_FILE, 'rb') as file:
            return web.Response(body=file.read(), content_type='text/html')
    await response.prepare(request)

    try:
        print('Some joined.')
        request.app['sockets'].append(response)

        # async for msg in response:
        #     if msg.type == web.WSMsgType.TEXT:
        #         for sock in request.app['sockets']:
        #             if sock is not response:
        #                 await sock.send_str(msg.data)
        #             else:
        #                 return response
        # return response
        async def desync(it):
            for mess in it: yield mess

        async for x in desync(request.app['news']):
            for sock in request.app['sockets']:
                if sock is response:
                    await sock.send_str(json.dumps(x))

        async for msg in response:
            if msg.type == web.WSMsgType.TEXT:
                if msg.data == 'close':
                    await response.close()
                else:
                    await response.send_str(msg.data)
            elif msg.type == web.WSMsgType.ERROR:
                print('ws connection closed with exception %s' %
                      response.exception())

        return response

    finally:
        request.app['sockets'].remove(response)
        print('Some disconnected.')


async def on_shutdown(app: web.Application):
    for sock in app['sockets']:
        await sock.close()


async def postnews(request: web.Request):
    data = await request.post()
    title = data['title']
    text = data['text']
    date = str(datetime.datetime.now().strftime('%H:%M %d.%m.%Y'))
    result = {
        'title': title,
        'text': text,
        'date': date
    }

    request.app['news'].append(result)

    resp = {'status': 'ok'}

    for sock in request.app['sockets']:
        await sock.send_str(json.dumps(result))

    return web.json_response(resp)


def init():
    app = web.Application()
    logging.basicConfig(level=logging.DEBUG)
    app["sockets"] = []
    app["news"] = [{
        'title': 'Новость 1',
        'text': 'Текст новости 1',
        'date': '00:10 22.12.2022'
    }, ]
    app.add_routes([
        web.get('/', wshandler),
        web.post('/post', postnews)
    ])
    app.router.add_get('/', wshandler)
    app.on_shutdown.append(on_shutdown)

    return app


if __name__ == '__main__':
    web.run_app(init())
