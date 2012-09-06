import zipfile
from io import BytesIO
from shutil import copyfileobj

z = zipfile.ZipFile("../templates.zip", "r")
print(z.namelist())
s = BytesIO()
copyfileobj(z.open('templates/main.css', "r"), s)
print(s.getvalue().decode())
