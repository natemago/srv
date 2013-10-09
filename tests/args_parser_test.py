from argparse import ArgumentParser

parser = ArgumentParser(description="srv (serve) - Python 3 web server")
parser.add_argument("-p","--port", default="8000", type=int, required=False, dest="port", help="Server HTTP port. Server will bind to this port.")
parser.add_argument("-d", "--directory", default=".", required=False, dest="directory", help="Base directory. Srv will serve the content of this directory. Analogous to document root in Apache.")

args = parser.parse_args()
print(args)
