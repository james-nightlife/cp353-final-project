from flask import Flask, jsonify, render_template, request, redirect
import json, plotly
from flask_restx import Api, Resource
import requests
import plotly.graph_objs as go
import numpy as np
import os
from PIL import Image
import base64
from ml_model import TFModel

UPLOAD_FOLDER = './static/uploads'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

model = TFModel(model_dir='./ml-model/')
model.load()

api = Api(
    app, 
    title = "Finance API", 
    description = "API that collect income and expense data"
    )

f = open('income.json')
data = json.load(f)
f.close()

"""=================================================================== เซฟไฟล์ ==================================================================="""
def savedata():
    global data
    data = sorted(data, key=lambda k: k['date'])
    f = open('income.json', 'w')
    f.write(str(data).replace("'", '"'))

"""======== สร้างกราฟ ==============="""
def graphModify(x):
    ret = {}
 
    for i in x['data']:
        if str(i['date'])[0:7]+" I" not in list(ret.keys()) and str(i['date'])[0:7]+" E" not in list(ret.keys()):
            if i['status'] == "income":
                ret[str(i['date'])[0:7]+" I"] = i['value']
                ret[str(i['date'])[0:7]+" E"] = 0
            elif i['status'] == "expense":
                ret[str(i['date'])[0:7]+" E"] = i['value']
                ret[str(i['date'])[0:7]+" I"] = 0
        else:
            if i['status'] == "income":
                ret[str(i['date'])[0:7]+" I"] += i['value']
            elif i['status'] == "expense":
                ret[str(i['date'])[0:7]+" E"] += i['value']
    
    #ได้ ret
    i = []
    e = []
    month =[]
    for y in list(ret.keys()):
        if y[8:9] == 'E':
            e.append(ret[y])
        elif y[8:9] == 'I':
            i.append(ret[y])
    print(i)
    print(e)

    for y in list(ret.keys()):
        if y[0:7] not in month:
            month.append(y[0:7])

    trace1 = { "x": month, "y": e, "name": "Expense", "type": "bar", 'marker':{'color':'red' }}
    trace2 = { "x": month, "y": i, "name": "Income", "type": "bar", 'marker':{'color':'green' }}

    return [trace1, trace2]



"""=================================================================== แสดงผลข้อมูล ==================================================================="""
@api.route('/showdata')
class ShowData(Resource):
    @api.doc(responses={200: "Display List"})
    def get(self):
        return {'data': data}, 200

"""=================================================================== เพิ่มข้อมูล ==================================================================="""
@api.route('/insertdata')
class GetData(Resource):
    @api.doc(responses={403: 'Incomplete Data Request', 200: "Insert Successfully"})
    def post(self):
        key = list(api.payload.keys())
        if key == ['action', 'status', 'value', 'date']:
            date = api.payload['date']
            action = api.payload['action']
            status = api.payload['status']
            value = float(api.payload['value'])
            data.append({"action": action, "status": status, "value": value, "date": date})
            savedata()
            return api.payload, 201
        else:
            return {'error': 'incomplete requests'}, 403

"""=================================================================== ลบข้อมูล ==================================================================="""       
@api.route('/deletedata/<int:index>')
@api.doc(params={'index': 'Index of a specific list'})
class DeleteData(Resource):
    @api.doc(responses={403: 'Index Not Found', 200: "Delete Successfully"})
    def delete(self, index):
        if index < len(data):
            data.pop(int(index))
            savedata()
            return {"status": "Delete Successfully"}
        else:
            
            return {"status": "Index Not Found"}, 403

"""=================================================================== แก้ไขข้อมูล ==================================================================="""
@api.route('/editdata/<int:index>')
@api.doc(params={'index': 'Index of a specific list'})
class EditData(Resource):
    @api.doc(responses={403: 'Index Not Found', 200: "Delete Successfully"})
    def put(self, index):
        print(len(data))
        print(index)
        if index < len(data):
            keys = list(api.payload)
            print(keys)
            for i in keys:
                print(data[index])
                data[index][i] = api.payload[i]
            savedata()
            return {'status': 'Edit Successfully', 'data': data[index]}
        else:
            return {'status': 'Index Not Found'}, 403

"""=================================================================== แสดงผลรวมรายรับ รายจ่าย ==================================================================="""
@api.route('/summarize')
class Summarize(Resource):
    @api.doc(responses={200: "Calculated"})
    def get(self):
        income = 0.0
        expense = 0.0
        for i in data:
            if i['status'] == 'income':
                income += i['value']
            elif i['status'] == 'expense':
                expense += i['value']
        difference = income - expense

        return {'Income': income, 'Expense': expense, 'Difference': difference}


"""=================================================================== Client Display ==================================================================="""
@app.route('/home')
def home():
    url = "http://localhost:5000/showdata"
    urldata = requests.get(url).json()

    sumurl = "http://localhost:5000/summarize"
    sum = requests.get(sumurl).json()

    newdata = graphModify(urldata)
    graph = [
            {
                'data':newdata, 
                'layout':{'barmode': 'group', 'title':'Monthly Income and Expense Statistics', 'paper_bgcolor': 'rgba(0,0,0,0)', 'plot_bgcolor': 'rgba(0,0,0,0)'}
            }
        ]
    ids = ['Graph-{}'.format(i) for i, _ in enumerate(graph)]
    graphJSON = json.dumps(graph, cls=plotly.utils.PlotlyJSONEncoder)


    return render_template("home.html", data=urldata, sum=sum, ids = ids, graphJSON=graphJSON)

"""============================================ ลบข้อมูล ==========================================================================="""
@app.route('/home/delete', methods=['GET'])
def delete():
    if request.args.get('id'):
        url = "http://localhost:5000/deletedata/"+request.args.get('id')
        print(url)
        urldata = requests.delete(url).json()
        return redirect("../home")

"""============================================ เพิ่มข้อมูล ==========================================================================="""
@app.route('/home/add', methods=['POST'])
def add():
    if request.method == 'POST':
        dict_data = {'action': request.form['action'], 'status': request.form['status'], 'value': request.form['value'], 'date': request.form['date']}
        print(dict_data)
        url = "http://localhost:5000/insertdata"
        urldata = requests.post(url, json = dict_data)
        return redirect("../home")


"""============================================ แก้ไขข้อมูล ==========================================================================="""
@app.route('/home/edit', methods=['POST'])
def edit():
    if request.method == 'POST':
        dict_data = {'action': request.form['action'], 'status': request.form['status'], 'value': float(request.form['value']), 'date': request.form['date']}
        url = "http://localhost:5000/editdata/"+ request.form['index']
        print(url)
        urldata = requests.put(url, json = dict_data)
        return redirect("../home")

""" Machine Learning """
@app.route('/home/currency', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file1' not in request.files:
            return 'there is no file1 in form!'
        file1 = request.files['file1']
        path = os.path.join(app.config['UPLOAD_FOLDER'], file1.filename)
        file1.save(path)

        image_1 = Image.open(path)
        outputs = model.predict(image_1)



        return render_template('prediction.html', pred_result=outputs, path=file1.filename)

    return render_template('upload.html')