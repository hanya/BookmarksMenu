#  Copyright 2012 Tsutomu Uchino
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# Command URL used in Bookmarks Menu is not valid URL. 
# It is unicode instance and the following characters are 
# % encoded in query strings: =, &
# Do not combine with functions provided by urlparse and urllib modules.

def bk_quote(s):
    s = s.replace("=", "%3D")
    s = s.replace("&", "%26")
    return s


def bk_unquote(s):
    s = s.replace("%3D", "=")
    s = s.replace("%3d", "=")
    s = s.replace("%26", "&")
    return s


def bk_urlencode(query):
    """ Construct query string from dict. """
    l = []
    for k, v in query.iteritems():
        l.append(bk_quote(k) + "=" + bk_quote(v))
    return "&".join(l)


def bk_parse_qs(qs):
    """ Parse query string created by bk_urlencode and returns 
    dict. This function ignores multiple values.
    """
    return dict(bk_parse_qsl(qs))


def bk_parse_qsl(qs):
    """ Parse query strings created by bk_urlencode and returns 
    tuple of key, value pair. The value is not a list but unicode. """
    pairs = qs.split("&")
    r = []
    for name_value in pairs:
        nv = name_value.split("=", 1)
        if len(nv) == 2:
          r.append((bk_unquote(nv[0]), bk_unquote(nv[1])))
    return r


def bk_command_parse(command):
    """ Parse command and returns tuple of items. 
    
    """
    path = ""
    query = ""
    main_query = command.split("?", 1)
    main = main_query[0]
    scheme_path = main.split(":", 1)
    scheme = scheme_path[0]
    if len(scheme_path) == 2:
        path = scheme_path[1]
    if len(main_query) == 2:
        query = main_query[1]
    
    return main, scheme, path, query

