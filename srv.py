#!/usr/bin/python3

from http.server import HTTPServer as HTTPServer
from http.server import SimpleHTTPRequestHandler as SimpleHTTPRequestHandler
from io import BytesIO as BytesIO
import uuid
import re
import shutil
from urllib import parse
import urllib

import socket

class BaseMappedHander:
    def __init__(self):
        pass
    
    
    def process(self, request, response):
        pass
    
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
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True, handlersMapping={}):
        HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.handlers = handlersMapping
        


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
        
    def get_session(self):
        if self.session == None:
            self.session = HTTPSession()
        
    def forward(self, to_path):
        pass



class HTTPResponse:
    def __init__(self):
        self.code = 200
        self.message = ""
        self.error = False
        self.out_stream = False
        self.headers = {}
        
    def write(self, msg):
        pass
    
    def send_error(self, code, message=""):
        pass
    
    def redirect(self, to_url):
        pass

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
            #mname = 'do_' + self.command
            #if not hasattr(self, mname):
            #    self.send_error(501, "Unsupported method (%r)" % self.command)
            #    return
            #method = getattr(self, mname)
            self.do_handle_one_request(self.path)
            self.wfile.flush() #actually send the response if not already done.
        except socket.timeout as e:
            #a read or a write timed out.  Discard this connection
            self.log_error("Request timed out: %r", e)
            self.close_connection = 1
            return
    
    def do_handle_one_request(self, path):
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
                    request = self.construct_request()
                    response = self.construct_response()
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
        pass
    
    def process_default_request(self):
        mname = 'do_' + self.command
        if not hasattr(self, mname):
            self.send_error(501, "Unsupported method (%r)" % self.command)
            return
        method = getattr(self, mname)
        method()


class TestHandler (BaseMappedHander):
    def process(self, request, response):
        BaseMappedHander.process(self, request, response)
        print("yaay")

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
            "handler": BaseMappedHander()
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
