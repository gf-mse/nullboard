#!/usr/bin/python3

import sys
import os
import re # filename filters

from os.path import join as path_join
import glob # for stashing and unstashing

## import time
from time import localtime, strftime

if 1:
    from flask import Flask, request, jsonify, abort, make_response # , json
    import json
else:
    from flask import Flask, request, json, jsonify, abort, make_response

# [ https://flask-cors.readthedocs.io/en/3.0.10/ ]
from flask_cors import CORS

## import socket
from socket import gethostname, gethostbyaddr

#
# IP filtering
#

# [ https://stackoverflow.com/questions/3837069/how-to-get-network-interface-card-names-in-python/12261059#12261059 ]
from netifaces import interfaces, ifaddresses, AF_INET
# [ https://stackoverflow.com/questions/819355/how-can-i-check-if-an-ip-is-in-a-network-in-python/1004527#1004527 ]
from ipaddress import ( IPv4Network as ip_network, IPv4Address as ip_address)

# // debug
## import inspect as I

# ---------------------------------------------------------------------
# constants, globals, etc

## _DEBUG = 1
_DEBUG = bool( os.environ.get('DEBUG', '0').strip() )
if _DEBUG:
    import cgitb
    cgitb.enable(format='text')

RE_SPECIAL_AS_TEXT = r'''[\%\&\"\,\)\@\^\.\;\!\/\}\*\[\(\>\\\?\#\`\{\]\:\+\~\\'\|\$\<]+'''
RE_SPECIAL = re.compile( RE_SPECIAL_AS_TEXT )



SERVER_LISTEN_ON_ALL_INTERFACES = '0.0.0.0'

LOCALHOST_DEFAULT_BACKUP_PORT = 10001
LOCALHOST_DEFAULT_BACKUP_SERVER_SETTINGS = ('127.0.0.1', LOCALHOST_DEFAULT_BACKUP_PORT)

HOSTNAME = gethostname()
HOST_ALIASES = { 'localhost' : HOSTNAME }


BACKUP_DIRECTORY = os.environ.get('BACKUP_DIR', '.')
if BACKUP_DIRECTORY in ('.', ''):
    print("# nb: set 'BACKUP_DIR' environment variable to make it the root of backups directory tree")

BACKUP_VERIFY_TOKEN = os.environ.get('ACCESS_TOKEN', None)

app = Flask(__name__)
CORS(app)


# [ https://stackoverflow.com/questions/14853694/python-jsonify-dictionary-in-utf-8/39561607#39561607 ]
## app.config['JSON_AS_ASCII'] = False

# // initial notes, see the README file for more
ON_BACKUP_PROTOCOL = """

    Looking at the code --
    
        https://github.com/apankrat/nullboard/blob/46525687c4da36b36f123af4364a1c193fedf637/nullboard.html#L2063
        https://github.com/apankrat/nullboard/blob/46525687c4da36b36f123af4364a1c193fedf637/nullboard.html#L2448

     -- as well as at wireshark dumps of local / remote backup session attempts --

        "tshark -i lo -w testsession.`date +%F-t-%s`.dump -f 'port 10001' -P -t ad"

     -- there are (up to) three REST API commands in action:
     
        OPTIONS
        PUT
        DELETE

    They are mostly happy with a 200 response, except for when they are not, 
    and in that case they seem to be expecting a 201 or a 204 depending on the context
    // see e.g. https://stackoverflow.com/a/827045/558008 )

    Apparently the data that we receive is _not_ json but is 'application/x-www-form-urlencoded',
    and we have to parse and extract json from its 'data' field )

"""

# // initial notes, see the README file for more recent updates
BACKUP_LOGIC_DESCRIPTION = """

    So far the idea is that we save everything, with the current pattern being
      ./config/YYYY-MM-DD/HH/MM , where MM is ~ "minutes mod 10" : 10, 20, 30 ...,
    and the older files being overwritten with the newer ones -- 
       -- so that we shall be able to recover from a browser update ))
       
    In addition to that, we save the '.data' part to a file with the same ".nbx"
    extension as is produced by Nullboard itself )

"""


# ---------------------------------------------------------------------
# quick debug prints

# // of course there is logging, but I have no time for this 
class DebugOutput:

    def __init__(self, request):
        self.logline = f"{request.origin} => {request.host} : {request.method.lower()} : {request.url!r}"

    @classmethod
    def format(cls, fmt, *args):
        """ uses % for *args if they exist """

        text = fmt
        if args:
            text = fmt % args

        return text


    @classmethod
    def output(cls, fmt, *args, **kwargs):
        """ uses f"" for keyword arguments, % for *args, and **kwrags to control print() """
        if _DEBUG:
            text = cls.format(fmt, *args)
            print( text, file=sys.stderr, **kwargs )

    # a shorter alias
    out = output

    def _dbg(self, fmt, *args, **kwargs):
        message = self.format(fmt, *args)
        text = f"# {self.logline} : {message}"

        # memorize last '\n'
        end = ''
        if text.endswith('\n'):
            text = text[:-1]
            end = '\n'

        formatted = '# ' + '\n# '.join(text.split('\n')) + end
        self.output( formatted, **kwargs )

    # a shortcut
    __call__ = _dbg


# an alias )
Dbg = DebugOutput

# another alias )
_debug = DebugOutput.output

# ---------------------------------------------------------------------
# code ))

def get_address_by_iface(interface_name):
    """ get the (first) ip address as a string """

    ip_addr = ifaddresses(interface_name)[AF_INET][0]['addr']
    return ip_addr


def get_network_by_iface(interface_name):
    """ get ip network as an ipaddress module object ) """

    ip_addr = get_address_by_iface(interface_name)
    netmask = ifaddresses(interface_name)[AF_INET][0]['netmask']

    subnet = ip_network( f"{ip_addr}/{netmask}", strict = False )

    return subnet


# ---------------------------------------------------------------------

# [ https://stackoverflow.com/questions/10434599/get-the-data-received-in-a-flask-request ]
# // [ https://flask.palletsprojects.com/en/2.2.0/api/#flask.Request.json ]
# // [ https://flask.palletsprojects.com/en/2.2.0/api/#flask.Request.form ]
def get_request_data( request ):
    """
        shall return a parsed json - alike structure, or None
    """
    
    data = None
    if request.mimetype == 'application/x-www-form-urlencoded':
        data = request.form
    # [ https://flask.palletsprojects.com/en/2.2.0/api/#flask.Request.is_json ]:
    #  -> "either application/json or application/*+json"
    elif request.mimetype in ('application/json', 'text/javascript'):
        # [ https://stackoverflow.com/questions/20001229/how-to-get-posted-json-in-flask ]
        ## data = request.get_json(force=True)
        data = request.get_json()

    return data


def get_json_data( request ):
    """
        get the .data part of the board
    """
    
    _dbg = Dbg(request)
    
    json_data = None
    if request.mimetype == 'application/x-www-form-urlencoded':
        data = request.form
        if getattr(data, '__getitem__', None) is not None:
            ## print(f"get_json_data() => {data}", file=sys.stderr)
            ## json_data = json.loads(data.get('data', '{}'))
            json_as_text = data.get('data', '{}')
            json_data = json.loads(json_as_text) if json_as_text else {}

    elif request.mimetype in ('application/json', 'text/javascript'):
        # [ https://stackoverflow.com/questions/20001229/how-to-get-posted-json-in-flask ]
        ## data = request.get_json(force=True)
        json_data = request.get_json()

    else:
        _dbg(f"[dbg] unexpected request type: {request.mimetype!r}")

    return json_data
    

def get_request_board_data( request ):
    """
        shall return a parsed json - alike structure, or None
    """

    assert request.mimetype == 'application/x-www-form-urlencoded'
    data = get_json_data( request )

    return data


# ---------------------------------------------------------------------

def time_to_subpath(t_tuple):
    """ "2021-12-31 18:12" -> '2021-12-31/18/10'  """

    minutes = ( t_tuple.tm_min // 10 ) * 10   
    datedir = strftime('%F/%H')
    
    result = path_join(datedir, str(minutes))
    
    return result


def time_to_filename( t_tuple ):
    """ add the current date / time to the filename """

    # just use the current date for now )
    datestamp = strftime('%F', t_tuple)
    return datestamp


def get_host_name(request):

    hostname = None
    if request is not None:
        # [ https://werkzeug.palletsprojects.com/en/2.0.x/wrappers/#werkzeug.wrappers.Request.remote_addr ]
        ip_addr = request.remote_addr
        hostname = gethostbyaddr(ip_addr)[0]
        hostname = HOST_ALIASES.get(hostname, hostname).lower()

    return hostname


def sanitize_filename(filename, _re_filter = RE_SPECIAL):

    result = _re_filter.sub('_', filename)
    return result

# // makes a list of essential filename parts from available components (board data, time, string prefix/suffix parts)
def make_filename_parts( board_id, json_data=None, t_tuple=None, prefix=None, suffix=None, use_rev = True ):
    """ ( ... , 'data latest nbx'.split() ) => [ hostname, board_name, {datestamp}, data.latest.nbx ] """

    _dbg = Dbg(request)

    ## # this is expected to come from a "/board/<id>" route and shall not be None ))
    ## assert board_id

    board_name = None
    board_rev = None
    if json_data:
        if board_id:
            _board_id = int(board_id)
            board_id_ = json_data.get('id', -1)
            ## _dbg(f"[dbg] board_id (path) {board_id!r} ({_board_id!r}) == board_id (data) {board_id_!r} ?")
            assert _board_id == board_id_

        board_name = json_data.get('title', '').strip()
        board_name = sanitize_filename( board_name )
        # remove spaces
        # board_name = '.'.join(board_name.split())
        board_name = '_'.join(board_name.split())
        
        if use_rev:
            board_rev = json_data.get('revision', None)
        else:
            board_rev = ''

    timestamp = None
    if t_tuple is not None:
        timestamp = time_to_filename( t_tuple )

    parts = (prefix, board_name, board_id, board_rev, timestamp, suffix)
    parts = [ str(p) for p in parts if p ]

    return parts


def make_filename( board_id, json_data=None, t_tuple=None, prefix=None, suffix=None, use_rev = True ):
    """ ( ... , 'data latest nbx'.split() ) => hostname.board_name.{datestamp}.data.latest.nbx """

    parts = make_filename_parts( board_id=board_id, json_data=json_data, t_tuple=t_tuple, prefix=prefix, suffix=suffix, use_rev = use_rev )

    filename = '.'.join(parts)
    
    return filename



def save_board_data(board_id, request):
    """
        attempts to save to a path under cwd )
        
        nb(1): 'board_id' is essential, and we expect bool(board_id) to be true )        
        nb(2): we expect 'board_id' to come from request path, e.g. '/board/<board-id>'
    """

    _dbg = Dbg(request)

    ## result = '' 
    ## retcode = RETURN_200_OK

    retcode = RETURN_200_UPDATED
    # OK, looks like it wants something json-alike in return
    result = '{}'

    full_data_json = get_request_data(request)
    board_data_json = get_request_board_data(request)

    t_now = localtime()
    hostname = get_host_name( request )
    time_subdir = time_to_subpath(t_now)

    # filename_full   : save everything
    # filename_board  : save the board / "data" part only
    # filename_latest : save the most recent board version as "lastest"

    filename_full   = make_filename( board_id, json_data=board_data_json, t_tuple=t_now, prefix=hostname, suffix='full' )
    filename_board  = make_filename( board_id, json_data=board_data_json, t_tuple=t_now, prefix=hostname, suffix='nbx' )
    filename_latest = make_filename( board_id, json_data=board_data_json, t_tuple=t_now, prefix=hostname, suffix='latest-saved.nbx', use_rev = False )

    dir_latest = path_join(BACKUP_DIRECTORY, 'boards')
    dir_full   = path_join(BACKUP_DIRECTORY, 'boards', 'full', hostname, time_subdir)
    dir_board  = path_join(BACKUP_DIRECTORY, 'boards', 'nbx',  hostname, time_subdir)

    for directory, filename, data in ( (dir_latest, filename_latest, board_data_json)
                                     , (dir_full,   filename_full,   full_data_json )
                                     , (dir_board,  filename_board,  board_data_json)
                                     ):
        if data is not None:
            os.makedirs(directory, exist_ok = True)
            fullname = path_join(directory, filename)
            with open(fullname, 'wt') as f:
                f.write(json.dumps(data, indent=4, sort_keys=True, ensure_ascii=False))            


    # // if we are successful -- let us delete old revisions
    # // // TODO : clean this up
    full_parts   = make_filename_parts( board_id, json_data=board_data_json, t_tuple=t_now, prefix=hostname, suffix='full' )
    board_parts  = make_filename_parts( board_id, json_data=board_data_json, t_tuple=t_now, prefix=hostname, suffix='nbx' )
    
    for directory, parts in ( (dir_full,   full_parts,   )
                            , (dir_board,  board_parts,  )
                            ):

        ##  parts = (prefix, board_name, board_id, board_rev, timestamp, suffix)
        ##  parts = [ str(p) for p in parts if p ]
        parts[-3] = '*'
        filename_mask = '.'.join(parts)
        pathname_mask = path_join(directory, filename_mask)
        # [ https://stackoverflow.com/a/168424 ]
        files = list(  filter( os.path.isfile, glob.glob(pathname_mask) )  )
        if files:
            files.sort(key=lambda x: os.path.getmtime(x))
            files.reverse()
            # keep only last 5 revisions in this directory
            for fname in files[5:]:
                try:
                    os.unlink(fname)
                    _dbg( f"[info] deleted old revision {fname!r}" )
                except OSError as e:
                    # print(e)
                    _dbg( f"[error] failed to delete file {fname!r} : {e}" )


    # return None
    return result, retcode


def save_stashed_board(board_id, request):
    """
        attempts to save to a path under cwd )
        
        nb(1): 'board_id' is essential, and we expect bool(board_id) to be true )        
        nb(2): we expect 'board_id' to come from request path, e.g. '/stash/<board-id>'
    """

    ## result = '' 
    ## retcode = RETURN_200_OK

    retcode = RETURN_200_UPDATED
    # OK, looks like it wants something json-alike in return
    result = '{}'

    ## full_data_json = get_request_data(request)
    ## board_data_json = get_request_board_data(request)
    board_data_json = get_json_data(request)

    t_now = localtime()
    hostname = get_host_name( request )
    time_subdir = time_to_subpath(t_now)

    filename_json   = make_filename( board_id, json_data=board_data_json, t_tuple=None, prefix=None, suffix=hostname+'.latest.json' )
    # filename_yaml   = make_filename( board_id, json_data=board_data_json, t_tuple=None, prefix=None, suffix=hostname+'.latest.yaml' )

    dir_stashed = path_join(BACKUP_DIRECTORY, 'boards/stashed')

    if board_data_json is not None:
        os.makedirs(dir_stashed, exist_ok = True)
        fullname = path_join(dir_stashed, filename_json)
        with open(fullname, 'wt') as f:
            f.write(json.dumps(board_data_json, indent=4, sort_keys=True, ensure_ascii=False))            

    # return None
    return result, retcode



# [ https://flask.palletsprojects.com/en/2.1.x/quickstart/#about-responses ]
def load_stashed_board():
    """
        find the most recent board under 'boards/stashed' and return it
    """

    ## _dbg = Dbg(request)

    result  = {}
    retcode = RETURN_404_NOT_FOUND

    ## dir_stashed = path_join(BACKUP_DIRECTORY, 'boards/stashed')
    filename_mask = path_join(BACKUP_DIRECTORY, 'boards/stashed', '*.latest.json')
    # [ https://stackoverflow.com/a/168424 ]
    files = list(  filter( os.path.isfile, glob.glob(filename_mask) )  )
    if files:
        files.sort(key=lambda x: os.path.getmtime(x))
        latest = files[-1]

        with open(latest, 'rt') as f:
            result = json.loads(f.read())
            ## result = json.load(f)
            retcode = RETURN_200_OK

    ## # // [ https://stackoverflow.com/a/56265574 ]
    ## # [ https://github.com/pallets/flask/issues/478#issuecomment-166723852 ]
    return result, retcode


def save_other_data(board_id, dir, request):
    """
        attempts to save to a path under cwd )
        
        nb(1): 'board_id' is essential, and we expect bool(board_id) to be true )        
        nb(2): we expect 'board_id' to come from request path, e.g. '/board/<board-id>'
    """

    # default return values, could change later if needed
    result = '' 

    retcode = RETURN_200_OK

    # by default, don't be picky and agree to save empty datasets 

    data = get_request_data(request)

    if data is not None:

        # 2021-12-31 18:12 -> 2021-12-31/18/10
        t_now = localtime()

        #
        # save everything we've been sent
        #

        hostname = get_host_name( request )
        time_subdir = time_to_subpath(t_now)

        directory = path_join(BACKUP_DIRECTORY, dir, hostname, time_subdir)
        os.makedirs(directory, exist_ok = True)

        filename = make_filename( board_id, json_data=data, t_tuple=t_now, prefix=None, suffix='data' )
        fullname = path_join(directory, filename)

        with open( fullname, 'wt' ) as f:
            # [ https://stackoverflow.com/questions/14853694/python-jsonify-dictionary-in-utf-8/39561607 ]
            f.write(json.dumps(data, indent=4, sort_keys=True, ensure_ascii=False))

            # return something json-alike 
            result = '{}'

    # return None
    return result, retcode



# ---------------------------------------------------------------------
# handlers

# [ https://stackoverflow.com/questions/31637774/how-can-i-log-request-post-body-in-flask ]

RETURN_200_OK = RETURN_200_UPDATED = 200
RETURN_201_CREATED                 = 201
RETURN_204_NO_CONTENT              = 204

RETURN_403_FORBIDDEN               = 403
RETURN_404_NOT_FOUND               = 404
RETURN_418_I_AM_A_TEAPOT           = 418

RETURN_501_NOT_IMPLEMENTED         = 403


def handle_dummy_request(request):
    """ a request with no id (e.g. /board instead of /board/board-id ) """

    result  = ''
    retcode = RETURN_200_OK

    return (result, retcode)

handle_options_request = handle_dummy_request


def handle_test_request(request):
    """ a request with no id to test things -- does not seem to accept 200 as an answer """

    result  = ''
    ## retcode = RETURN_200_OK
    ## retcode = RETURN_201_CREATED
    retcode = RETURN_204_NO_CONTENT

    return (result, retcode)


def handle_board_request(request, board_id):

    _dbg = Dbg(request)

    # some default settings, probably not ideal
    result, retcode = (None, RETURN_418_I_AM_A_TEAPOT)

    if board_id is None: 
        if request.method == 'PUT':
            result, retcode = handle_test_request(request)
            ## result, retcode = handle_other_requests(request, case='unknown', board_id=board_id)
        elif request.method == 'DELETE':
            ## retcode = 204 # "no content"
            # // let's return a 200 OK for now, and see how that plays out )
            result, retcode = handle_dummy_request(request)
        else:
            result, retcode = handle_dummy_request(request)

    # Ok, now we have a board_id
    else: 
        ## if request.method in ('PUT', 'POST'):
        if request.method == 'PUT' :
            result, retcode = save_board_data(board_id, request)
        elif request.method == 'DELETE':
            ## os.system( f"mv ${dir}/${id} ${dir}/${id}.deleted")
            _dbg( f"[delete] ignoring delete request for board {board_id}" )
            result, retcode = handle_dummy_request(request)
        else:
            result, retcode = handle_dummy_request(request)

    return (result, retcode)


def handle_other_requests(request, case='config', board_id=None):
    """ save anything else under {case}/ """

    _dbg = Dbg(request)

    # some default settings, probably not ideal
    result = None;  retcode = RETURN_501_NOT_IMPLEMENTED

    ## if request.method in ('PUT', 'POST'):
    if request.method == 'PUT' :
        result, retcode = save_other_data(board_id, case, request)
    elif request.method == 'DELETE':
        ## os.system( f"mv ${dir}/${id} ${dir}/${id}.deleted")
        _dbg( f"[other] ignoring delete request for case {case!r} and board_id={board_id}" )
        pass
    else:
        result, retcode = handle_dummy_request(request)

    return (result, retcode)


def handle_any_request(case='board', board_id=None):

    _dbg = Dbg(request)
    _dbg.out('\n')

    ip_filter = app.config.get('ip_filter', lambda _ : True)
    ip_addr = request.remote_addr

    client_ip_accepted = ip_filter( ip_addr )
    if not client_ip_accepted:
        # [ https://flask.palletsprojects.com/en/1.1.x/api/#flask.abort ]
        abort(RETURN_403_FORBIDDEN)

    ## _dbg.out(f"[dbg] => have access token {BACKUP_VERIFY_TOKEN!r}\n")
    if BACKUP_VERIFY_TOKEN:
        access_token = request.headers.get('X-Access-Token', None)
        if access_token != BACKUP_VERIFY_TOKEN:
            _dbg.out(f"[warning] => got access token {access_token!r} different from what we expected!\n")
            abort(RETURN_403_FORBIDDEN)
            

    ## print("\n")
    ## logline = f"{request.origin} => {request.host} : {request.method.lower()} : {request.url!r}"
    ## print( f"# {logline} : {request.data} " )

    ## _dbg( f"{request.data}" )

    # [ https://stackoverflow.com/questions/797834/should-a-restful-put-operation-return-something ]

    ## result = None # this would result in a flask error 
    result = '' 

    retcode = RETURN_200_OK

    request_data = get_request_data(request)

    # debug
    if request_data is not None:
        text_data = json.dumps(request_data, indent=0)
        _dbg( f"[data] {text_data[:150]}..." )
    else:
        _dbg( f"[data] -" )


    #
    # for OPTIONS, id in our case is basically irrelevant
    #

    if request.method == 'OPTIONS':
        result, retcode = handle_options_request(request)

    else:

        if 'board' == case:
            result, retcode = handle_board_request(request, board_id=board_id)

        elif 'stash' == case: 
            if request.method == 'PUT':
                result, retcode = save_stashed_board(board_id=board_id, request = request)
            else:
                result, retcode = handle_dummy_request(request)

        elif 'unstash' == case: 
            if request.method == 'GET':
                result, retcode = load_stashed_board()                
            else:
                result, retcode = handle_dummy_request(request)

        else: 
            result, retcode = handle_other_requests(request, case=case, board_id=board_id)

        # [ https://stackoverflow.com/questions/7824101/return-http-status-code-201-in-flask ]

        ##      if result and not isinstance(result, (str, bytes)):
        ##          # // we should have set the response mimetype, I suppose,
        ##          # // but our response is actually quite likely ignored )
        ##          result = json.dumps(result)
        ##  
        ##      ret = (result, retcode)
        ##      # [ https://stackoverflow.com/q/11945523 ]
        ##      # [ https://stackoverflow.com/a/11945643 ]
        ##      if isinstance(result, dict):
        ##          ## result = jsonify(result)
        ##          ret = make_response(result, retcode)
        ##          ret.mimetype = 'application/json'
        ##
        ##  
        ##      return ret
        ##

    return result, retcode


# [ https://stackoverflow.com/questions/36076490/debugging-a-request-response-in-python-flask ]

# [ https://stackoverflow.com/questions/10434599/get-the-data-received-in-a-flask-request ]



# ---------------------------------------------------------------------
# routes

@app.after_request
def after(response):
    # todo with response
    if 0:
        if _DEBUG:
            print( f" <= status: {response.status}" )
            print( f" <= headers: {response.headers!r}")
            print( f" <= data: {response.get_data()}")
        return response

    _debug( f" <= status: {response.status}" )
    _debug( f" <= headers: {response.headers!r}")
    _debug( f" <= data: {response.get_data()}")

    return response


@app.before_request
def before():
    # todo with request
    if 0:
        if _DEBUG:
            # e.g. print request.headers
            print( f"\n-----")
            print( f" => headers: {request.headers!r}")
            print( f" => content-type: {request.content_type!r}")
            print( f" => mimetype: {request.mimetype!r}")
            print( f" => content-length: {request.content_length}")

    # e.g. print request.headers
    _debug( f"\n-----" )
    _debug( f" => headers: {request.headers!r}" )
    _debug( f" => content-type: {request.content_type!r}" )
    _debug( f" => mimetype: {request.mimetype!r}" )
    _debug( f" => content-length: {request.content_length}" )

    pass


## @app.route('/board/<id>', methods=['DELETE', 'GET','POST'])
# // [ https://flask.palletsprojects.com/en/1.1.x/api/#flask.Flask.add_url_rule ]
## @app.route('/board/<id>', methods=['PUT', 'DELETE', 'OPTIONS', 'GET', 'POST'], provide_automatic_options=True)
## @app.route('//board/<id>', methods=['PUT', 'DELETE', 'OPTIONS', 'GET', 'POST'], provide_automatic_options=True)
@app.route('/board/<id>', methods=['PUT', 'DELETE', 'OPTIONS'], provide_automatic_options=True)
def board_handler(id=None):
    return handle_any_request(case = 'board', board_id = id)

@app.route('/stash-board/<id>', methods=['PUT', 'DELETE', 'OPTIONS'], provide_automatic_options=True)
def stash_request_handler(id=None):
    # print("stash_request_handler()", file=sys.stderr)
    ## f = I.currentframe()
    ## print(f"stash_request_handler(): lo: {f.f_locals}, ac: {f.f_code.co_argcount}", file=sys.stderr)
    
    return handle_any_request(case = 'stash', board_id = id)

@app.route('/unstash-board', methods=['GET', 'OPTIONS'], provide_automatic_options=True)
def unstash_request_handler(id=None):
    return handle_any_request(case = 'unstash', board_id = id)


@app.route('/config', methods=['PUT', 'DELETE', 'OPTIONS'], provide_automatic_options=True)
def config_handler(id=None):
    return handle_any_request(case = 'config', board_id = id)


# ---------------------------------------------------------------------
# main

if __name__ == '__main__':

    # default settings
    LOCALHOST, DEFAULT_PORT = LOCALHOST_DEFAULT_BACKUP_SERVER_SETTINGS
    
    # another option 
    ALLHOSTS = SERVER_LISTEN_ON_ALL_INTERFACES

    # listen on a VPN interface by default
    if 0:
        IFACE_VPN = 'ourvpn'
    
        # [ https://stackoverflow.com/questions/3837069/how-to-get-network-interface-card-names-in-python/12261059#12261059 ]
        from netifaces import interfaces, ifaddresses, AF_INET

        ADDRESS = VPNADDR = ifaddresses(IFACE_VPN)[AF_INET][0]['addr']
    else:
        ADDRESS = LOCALHOST


    # [ https://flask.palletsprojects.com/en/2.0.x/api/#flask.Flask.run ]
    ## app.run(debug=True, host='0.0.0.0', port='10001') 

    HOST = os.environ.get('ADDR', ADDRESS)
    PORT = os.environ.get('PORT', DEFAULT_PORT)

    ## app.run(debug=_DEBUG, host=ALLHOSTS, port=PORT) 
    app.run(debug=_DEBUG, host=HOST, port=PORT) 

