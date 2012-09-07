#!/usr/bin/python3

from fileinput import close
from genericpath import isdir
from http.server import HTTPServer as HTTPServer, \
    SimpleHTTPRequestHandler as SimpleHTTPRequestHandler
from io import BytesIO as BytesIO, StringIO
from urllib import parse
import os.path
import posixpath
import re
import shutil
import socket
import time
import urllib
import uuid
import configparser
from zipfile import ZipFile


class HTTPException(Exception):
    def __init__(self, message="", code=500, cause=None):
        Exception.__init__(self)
        self.message = message
        self.code = code
        self.__cause__ = cause






class BaseMappedHander:
    def __init__(self, base_path=""):
        self.base_path = base_path
    
    
    def process(self, request, response):
        m = getattr(self, "do_" + request.method.upper())
        if m != None:
            m(request, response)
        else:
            response.send_error(501)
    
    def do_HEAD(self, request, response):
        pass
    def do_OPTIONS(self, request, response):
        pass
    def do_GET(self, request, response):
        pass
    def do_POST(self, request, response):
        pass
    def do_PUT(self, request, response):
        pass
    def do_DELETE(self, request, response):
        pass

class DispatcherHTTPServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, 
                 bind_and_activate=True, handlersMapping={},
                 srv_path=".",
                 configuration={}):
        HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.handlers = handlersMapping
        self.srv_path = srv_path
        self.initialize_server()
        self.configuration = configuration
    def initialize_server(self):
        pass
    

class HTTPSession:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.attributes = {}
        self.invalid = False
    
    def set(self, name, value):
        self.attributes[name] = value
        
    def rem(self, name):
        val = self.attributes.get(name)
        if val != None:
            del self.attributes[name]

class HTTPRequest:
    def __init__(self):
        self.method = ""
        self.query_string = ""
        self.in_stream = ""
        self.params = {}
        self.files = {}
        self.path = ""
        self.request_url = ""
        self.session = {}
        self.attributes = {}
        self.headers = {}
        self.remote_ip = ""
        self.host = ("",0) # Tupple (name, port)
        self.scheme = "HTTP"
        self.protocol_version = "1.0"
        self.forwarded = False
        
        
    def get_session(self):
        if self.session == None:
            self.session = HTTPSession()
        
    def forward(self, to_path):
        self.forwarded = True
        self.path = to_path



class HTTPResponse:
    def __init__(self):
        self.code = 200
        self.message = ""
        self.error = False
        self.out_stream = BytesIO()
        self.headers = {}
        
    
    def write(self, msg):
        self.out_stream.write(msg.encode())
    
    def send_error(self, code, message=None):
        self.code = code
        self.message = message
    
    def redirect(self, to_url):
        self.code = 301
        self.headers["Location"] = to_url

class DispatcherHTTPHandler(SimpleHTTPRequestHandler):
    def handle_one_request(self):
        """
        Overrides the method in the base HTTP handler
        """
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(414)
                return
            if not self.raw_requestline:
                self.close_connection = 1
                return
            if not self.parse_request():
                # An error code has been sent, just exit
                return
            self.do_handle_one_request(self.path)
            self.wfile.flush() #actually send the response if not already done.
        except socket.timeout as e:
            #a read or a write timed out.  Discard this connection
            self.log_error("Request timed out: %r", e)
            self.close_connection = 1
            return
    
    def do_handle_one_request(self, path, request=None):
        self.path = path
        self.log_message("PATH: %r (%r)", self.path, self.command)
        for name in self.server.handlers:
            self.log_message("\t Checking [%r]", name)
            hndDef = self.server.handlers[name]
            pattern = hndDef["pattern"]
            for p in pattern:
                if re.match(p, self.path):
                    self.log_message("\t\t-> match")
                    hnd = hndDef["handler"]
                    if(request == None):
                        request = self.construct_request()
                    response = self.construct_response()
                    hnd.base_path = os.path.abspath(self.server.srv_path) # TODO
                    hnd.process(request, response)
                    self.process_response(request, response)
                    return
                
        self.log_message("Pass to default...")
        self.process_default_request()
        self.log_message("Processing ended.")
    
    def construct_request(self):
        req = HTTPRequest()
        req.path, qm, req.query_string = self.path.partition("?")
        req.headers = self.headers
        req.method = self.command
        req.host = (self.server.server_name, self.server.server_port)
        req.remote_ip, remote_port = self.client_address
        req.scheme, sep, req.protocol_version = self.protocol_version.partition("/")
        req.in_stream = BytesIO()
        
        cl = self.headers.get("Content-Length")
        body = ''
        if(cl is not None):
            cl = int(str(cl))
            self.log_message("test - Content Length: %d"%(cl))
            req.in_stream.write(self.rfile.read(cl))
            print("REQUEST:\n%s"%req.in_stream.getvalue())
            body = req.in_stream.getvalue()
            if (body is not None):
                body = body.decode("utf-8") # FIXME: use the proper encoding here...
            else:
                body = ""
        req.params =  self._parse_request_params(req.method, body, "")
        print(req.params)
        return req
    
    def _parse_request_params(self, method, body, query_string):
        params = {}
        if( method == 'POST' or method == 'GET' ):
            body = urllib.parse.unquote(body)
            body = body[:-1]
            raw_params = urllib.parse.parse_qs(body) or {}
            params = self.__fix_params(raw_params)
            
        
        query_params = urllib.parse.parse_qs(query_string)
        if(query_params == None):
            query_params = {}
        query_params = self.__fix_params(query_params)
        if(params == None):
            params = {}
            
        params.update(query_params)
        return params
    def __fix_params(self, raw_params):
        params = {}
        for  name, value in raw_params.items():
            if (len(value) == 1):
                params[name] = value[0]
            else:
                params[name] = value
        return params
    
    def construct_response(self):
        return HTTPResponse()
    
    def process_response(self, request, response):
        if(request.forwarded):
            request.forwarded = False
            self.do_handle_one_request(request.path, request)
            return
        if(response.error):
            self.send_error(response.code, response.message)
            return
        if(response.code != 200):
            self.send_response(response.code, response.message)
        else:
            self.send_response_only(response.code, response.message)
        sent_headers = False
        for name,value in response.headers.items():
            self.send_header(name, value)
            sent_headers = True
        if(sent_headers):
            self.end_headers()
        
        #shutil.copyfileobj(response.out_stream, self.wfile)
        self.wfile.write(response.out_stream.getvalue())
        
    
    def process_default_request(self):
        mname = 'do_' + self.command
        if not hasattr(self, mname):
            self.send_error(501, "Unsupported method (%r)" % self.command)
            return
        method = getattr(self, mname)
        method()


    
class SimpleHandler (BaseMappedHander):
    
    DIRECTORY_LISTING_DOC_TEMPLATE = """
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>%(path)s</title>
<style type="text/css">
    body{
        font-family: monospace;
        background: #F0F0F0;
        color: gray;
    }
    td,th{
        font-family: monospace;
        text-align: right;
        padding-left: 30px;
        
    }
    
    th{
        color: #0084DB;
    }
    
    .header{
        font-weight: bold;
        font-size: 14px;
        padding: 10px;
    }
    .footer{
        color: gray;
        text-align: right;
        padding: 5px;
    }
    .content{
        border: 1px solid #D9D9D9;
        background: #fff;
        padding: 20px;
        
        
        -webkit-border-radius: 3px;
        -moz-border-radius: 3px;
        border-radius: 3px;
        box-shadow: 1px 1px 3px #0084DB;
    }
    
    a.link-dir{
        color: gray;
        font-weight: bold;
    }
    
    a.link-dir:HOVER{
        color: #D6A400;
    }
    
    a.link-file{
        color: gray;
        text-decoration: none;
    }
    
    a.link-file:HOVER{
        color: #D6A400;
    }
    .info-name{
        text-align: left;
    }
    
</style>
</head>
<body>
<div class="header">
    %(path)s (%(dir_path)s)
</div>
<div class="content">
    
    <table>
        <thead>
            <tr>
                <th class="info-name">Name</th>
                <th>Size</th>
                <th>Modified</th>
            </tr>
        </thead>
        <tbody>
            %(_FILES_LISTING_)s
        </tbody>
    </table>
    
</div>
<div class="footer">
srv, version %(server_version)s
</div>
</body>
</html>
"""
    DIRECTORY_ENTRY_TEMPLATE = """
             <tr>
                <td class="info-name"><a href="%(path)s" class="link-dir">%(name)s</a></td>
                <td class="info-size">%(size)s</td>
                <td class="info-modified">%(modified)s</td>
            </tr>"""
    FILE_ENTRY_TEMPLATE = """
             <tr>
                <td class="info-name"><a href="%(path)s" class="link-file">%(name)s</a></td>
                <td class="info-size">%(size)s</td>
                <td class="info-modified">%(modified)s</td>
            </tr>"""
    
    def do_GET(self, request, response):
        try:
            abspath = os.path.abspath(self.base_path + "/" + request.path)
            if(not abspath.startswith(self.base_path)):
                response.send_error(403)
            else:
                if(os.path.exists(abspath)):
                    self.do_process(request, response , abspath)
                else:
                    response.send_error(404)
        except IOError:
            response.send_error(404)
            
        
    def do_process(self, request, response, abspath):
        if isdir(abspath):
            if(not request.path.endswith('/') ):
                response.redirect(request.path + '/')
            else:
                self.process_dir(request, response, abspath)
        else:
            self.process_file(request, response, abspath)
    
    def process_dir(self, request, response, abspath):
        files = os.listdir(abspath)
        listingBuffer = []
        params = {}
        params["name"] = ".."
        params["path"] = request.path + ".."
        params["modified"] = time.ctime(os.path.getmtime(abspath + "/.."))
        params["full_path"] = abspath + "/.."
        params["size"] = "--"
        listingBuffer.append(self._format_dir(params))
        for fn in files:
            try:
                file_path = abspath + "/" + fn
                
                
                params = {}
                params["name"] = fn
                params["path"] = request.path + fn
                params["modified"] = time.ctime(os.path.getmtime(file_path))
                params["full_path"] = file_path
                if (os.path.isdir(file_path)):
                    params["size"] = "--"
                    listingBuffer.append(self._format_dir(params))
                else:
                    fh = open(file_path,"r")
                    params["size"] = os.fstat(fh.fileno())[6]
                    fh.close()
                    listingBuffer.append(self._format_file(params))
                    
            except IOError as e:
                print(e) 
        
        g_params = {}
        g_params["server_version"] = "0.1.0"
        g_params["dir_path"] = abspath
        g_params["path"] = request.path
        g_params["_FILES_LISTING_"] = ''.join(listingBuffer)
        response.write(self._format_directory_listing(g_params))
        
    
    def _format_file(self, params):
        return SimpleHandler.FILE_ENTRY_TEMPLATE % params
    
    def _format_dir(self, params):
        return SimpleHandler.DIRECTORY_ENTRY_TEMPLATE % params
    
    def _format_directory_listing(self, params):
        return SimpleHandler.DIRECTORY_LISTING_DOC_TEMPLATE % params
    
    def process_file(self, request, response, abspath):
        response.headers["Content-type"] = self._get_mime_type(request.path)
        try:
            fh = open(abspath, "rb")
            fs = os.fstat(fh.fileno())
            response.headers["Content-Length"] = fs[6]
            response.headers["Last-Modified"] = self._date_time_string(fs.st_mtime)
            
            shutil.copyfileobj(fh, response.out_stream)
            
            fh.close()
        except IOError as ioe:
            print(ioe)
            response.send_error(500, str(ioe))
    
    def _get_mime_type(self, path):
        base, ext = posixpath.splitext(path)
        if ext in SimpleHTTPRequestHandler.extensions_map:
            return SimpleHTTPRequestHandler.extensions_map[ext]
        ext = ext.lower()
        if ext in SimpleHTTPRequestHandler.extensions_map:
            return SimpleHTTPRequestHandler.extensions_map[ext]
        else:
            return SimpleHTTPRequestHandler.extensions_map['']
    
    def _date_time_string(self, timestamp=None):
        """Return the current date and time formatted for a message header."""
        if timestamp is None:
            timestamp = time.time()
        year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
        s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
                SimpleHTTPRequestHandler.weekdayname[wd],
                day, SimpleHTTPRequestHandler.monthname[month], year,
                hh, mm, ss)
        return s


_DEFAULT_CONFIG={
    "server":{
        "port": 8000,
        "serve_path": "."
    },
    "handlers":{
        "__default__": {
            "class": "SimpleHandler",
            "pattern":".*",
            "weight": -1
        }
    }
}

def read_config(fileName, defaults):
    config = configparser.ConfigParser()
    config.read(fileName)
    cnf = {}
    sections = config.sections()
    
    for section in sections:
        sec = {}
        cnf[section] = sec
        for name, value in config.items(section):
            cnf[section][name] = value
    
    return cnf
    


class ClassLoader:
    
    def __init__(self, context={}):
        self.context = context
        
    
    def load_class(self, path):
        module, dot, clazz =  path.rpartition('.')
        try:
            mod = __import__(module, context, context, [clazz], -1)
            constr = getattr(mod,clazz)
            return constr
        except Exception as e:
            raise Exception(e, "Cannot load class %s"%path)

    def get_instance(self, class_name, params=None):
        clz = self.load_class(class_name)
        instance = None
        if params == None:
            instance = clz()
        else:
            instance = clz(*params)
        
        return instance



class ZipLoader:
    _ZIP_ARCHIVE_PATTERNS = ['.*\\.zip','.*\\.jar']
    OVERRIDE = 0
    IGNORE = 1
    IMMEDIATE = 2
    LAZY = 4
    def __init__(self, path=[], policy=None, loading=None):
        self.path = path
        self.policy = policy or self.OVERRIDE
        self.loading = loading or self.LAZY
        self.cache = {}
        self.scan()
    
    def scan(self):
        for p  in self.path:
            self._scan(p)
    
    def _scan(self, file_path):
        if(isinstance(file_path, str) and os.path.isdir(file_path)):
            names = os.listdir(file_path)
            for n in names:
                self._scan(file_path + '/' + n)
        elif (isinstance(file_path,BytesIO)):
            self._read_zip_file(file_path)
        else:
            if(self._is_zip_archive(file_path)):
                self._read_zip_file(file_path)
    
    def _read_zip_file(self, zf):
        try:
            zh = ZipFile(zf, "r")
            names = zh.namelist()
            for name in names:
                existing = self.cache.get(name)
                load_now = False
                if existing != None:
                    if self.policy == ZipLoader.OVERRIDE:
                        load_now = True
                else:
                    load_now = True
                
                if(load_now):
                    entry = {}
                    entry["name"] = name
                    entry["file"] = zh
                    entry["file_name"] = zf
                    if(self.loading == ZipLoader.IMMEDIATE):
                        entry["content"] = self._load_from_archive(name, zh)
                    self.cache["name"] = entry
                 
        except Exception as e:
            pass
            
    
    def _load_from_archive(self, name, zip_file):
        s = BytesIO()
        shutil.copyfileobj(zip_file.open(name, "r"), s)
        return s.getvalue()
    
    def _is_zip_archive(self, path):
        for pattern in ZipLoader._ZIP_ARCHIVE_PATTERNS:
            if (re.match(pattern, path, re.I)):
                return True
        return False
    
    
    def get_resource(self, name):
        rc = self.cache.get(name)
        if rc != None:
            content = rc.get("content")
            if content == None and self.loading == ZipLoader.LAZY:
                    content = self._load_from_archive(name, rc["file"])
                    rc["content"] = content
            return content
        
        return None
    
    def get_resource_str(self, name):
        rc = self.get_resource(name)
        if rc != None:
            b = BytesIO()
            shutil.copyfileobj(rc, b)
            return b.decode()
        return None

    
def run_server(server_class=HTTPServer, 
         handler_class=SimpleHTTPRequestHandler,
                   port=8000,
                   address=''):
    """
    The most basic HTTP server.
    """
    print("Server is started and listens on port: %d"%port)
    server_address = (address, port)
    httpd = server_class(server_address, handler_class,handlersMapping={
       "dispatcher":{
            "pattern":["/.*"],
            "handler": SimpleHandler()
        }
    })
    httpd.serve_forever()
    
if __name__ == "__main__":
   print(" :: server staring ...")
   try:
      run_server(DispatcherHTTPServer, DispatcherHTTPHandler)
   except KeyboardInterrupt:
      print ("\n:: forced ::")
   print(" :: server shut down ::")



# base64 encoded ZIP file of the templates dir and other initial resources
_INITIAL_RC = """
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
6AMAAFBLBQYAAAAABQAFAMEBAACNIAAAAAA="""
# -- end of Base 64 string resource

_DEFAULT_RC_LOADER = ZipLoader([BytesIO(_INITIAL_RC.encode())])
