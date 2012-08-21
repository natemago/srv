#!/usr/bin/python3

from http.server import HTTPServer as HTTPServer
from http.server import SimpleHTTPRequestHandler as SimpleHTTPRequestHandler
from io import BytesIO as BytesIO
import uuid
import re
import shutil
from urllib import parse
import urllib
import posixpath

import socket
from io import StringIO
from genericpath import isdir
import os.path
import time
from fileinput import close


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
                 srv_path="."):
        HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.handlers = handlersMapping
        self.srv_path = srv_path


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
        self.out_stream = StringIO()
        self.headers = {}
        
    
    def write(self, msg):
        self.out_stream.write(msg)
    
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
        
        shutil.copyfileobj(BytesIO(response.out_stream.getvalue().encode() ), self.wfile)
        
    
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
            fh = open(abspath, "r")
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
