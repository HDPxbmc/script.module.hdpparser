#! /usr/bin/env python
# coding=utf-8
#   Author: jackyspy
#   Year: 2014
#
#   Distributed under the terms of the GPL (GNU Public License)
#
#   UliPad is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
import sys
import urlparse
import time
from urllib import quote_plus
import xbmc
import xbmcplugin
import xbmcgui
try:
    reload(sys)
    sys.setdefaultencoding('utf-8')
except:
    pass

from hdpparser import man, serialize, util, ParserError, cache

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

import xbmcutils


plugin_url = sys.argv[0]
handle = int(sys.argv[1])
params = dict(urlparse.parse_qsl(sys.argv[2].lstrip('?')))


def make_plugin_url(link_info, plugin_id=xbmcutils.PLUGIN_ID, plugin_path='/'):
    url = 'plugin://%s%s' % (plugin_id, plugin_path)

    url_params = []
    for k, v in link_info.iteritems():
        if isinstance(v, (dict, tuple, list)):
            url_params.append('params=' + serialize.dumps(v))

            continue

        url_params.append('%s=%s' % (k, quote_plus(str(v))))

    if url_params:
        url = url + '?' + '&'.join(url_params)

    return url


def handle_parse_result(res):
    if 'redirect' in res:
        _redirect_url(res)
    elif 'list' in res:
        _show_folder(res)
    elif 'file' in res:
        _show_file(res)


def _redirect_url(res):
    url = res['redirect']

    if isinstance(url, dict):
        url = make_plugin_url(url)

    xbmcutils.update_plugin_url(url)


def _create_list_item(item, isdir=False):
    url = item.get('link', '')
    if not isinstance(url, basestring):
        url = ''

    li = xbmcgui.ListItem(
        label=xbmcutils.colorize_title(item.get('title'), item.get('color')),
        iconImage=xbmcutils.translate_icon_url(
            item.get('icon', item.get('thumb'))),
        thumbnailImage=item.get('thumb', ''),
        path=url
    )

    return li


def _show_folder(res):
    item_list = res['list']
    for item in item_list:
        isdir = item.get('isdir', 0) == 1

        li = _create_list_item(item, isdir)

        url = item['link']
        if isinstance(url, dict):
            url = make_plugin_url(url)

        elif not isdir:
            if not item.get('direct_url'):
                params = util.copy_dict_value(
                    item, keys=['title', 'icon', 'thumb', 'link'])
                url = make_plugin_url(
                    {'uri': url, 'parser': 'playurl', 'params': params})

            # li.setProperty('mimetype', 'video/x-msvideo') #防止列出视频时获取mime type
            li.setProperty('IsPlayable', 'true')  # setResolvedUrl前必需

        xbmcplugin.addDirectoryItem(handle, url, li, isdir)

    xbmcplugin.endOfDirectory(handle)


def _show_file(res):
    item = res['file']
    url = item['link']

    li = _create_list_item(item)

    if isinstance(url, dict):
        xbmcutils.update_plugin_url(make_plugin_url(item))

    elif res.get('set_resolved_url'):
        xbmcplugin.setResolvedUrl(handle, True, li)

    else:
        xbmc.Player().play(url, li)


def set_callbacks():
    import bdyun_ui
    parser = man.get_parser('baiduyun')
    parser.set_get_captcha_func(bdyun_ui.get_captcha)


def set_cache():
    try:
        import StorageServer
    except:
        xbmc.log('StorageServer not found')
        return

    dumps = util.json.dumps
    loads = util.json.loads

    class MyCache:

        def __init__(self):
            self._cache = StorageServer.StorageServer(xbmcutils.PLUGIN_ID, 24)

        def get(self, key):
            stored_str = self._cache.get(key).strip()
            if not stored_str:
                return

            wrapped_val = loads(stored_str)
            if 0 < wrapped_val['exp'] < time.time():
                self._cache.delete(key)

                return

            return wrapped_val['val']

        def delete(self, key):
            self._cache.delete(key)

        def set(self, key, value, expire=None):
            wrapped_val = {
                'val': value,
                'exp': 0 if expire is None else int(time.time() + expire)
            }

            self._cache.set(key, dumps(wrapped_val))

    cache.set_cache_obj(MyCache())


def main():
    uri = params.get('uri', '')
    p = params.get('params')

    if p:
        p = serialize.loads(p)

        xbmc.log(util.json.dumps(p))

    try:
        parse_result = man.parse(uri, params.get('parser'), p)

        if parse_result is not None:
            handle_parse_result(parse_result)

    except ParserError as e:
        xbmc.log(str(e), xbmc.LOGERROR)

        errmsg = [
            u'解析器：%s  代码：%s' % (e.parser, e.errno),
            u'错误原因：%s' % e.errmsg
        ]

        orig_exc = e.exc
        extra_data = e.data.copy()
        exc_info = extra_data.pop('exc_info', '')

        if exc_info:
            errmsg.append(u'详细信息：%s\n' % exc_info)
        elif orig_exc:
            errmsg.append(u'原始错误：%s\n' % repr(orig_exc))
        elif extra_data:
            errmsg.append(u'其他信息：%s\n' % repr(extra_data))

        xbmcgui.Dialog().ok(u'地址解析出错', *errmsg)


if __name__ == '__main__':
    set_cache()
    set_callbacks()

    main()
