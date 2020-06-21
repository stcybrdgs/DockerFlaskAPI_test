"""
you want api to:
- register users
- give each user 1 token
- store a sentence on db for 1 token
- retrieve stored sentence on db for 1 token

lu password storing, hashing, salting

RESOURCE PARAMETERS (rules for building the api)
Resource            Address         Protocol        PARAMETERS          Response Status Codes
---------------------------------------------------------------------------------------------
Register User       /register       POST            user-pw str         200 ok
Store Sentence      /store          POST            user/pw/str         200 ok | 301 out of tokens | 302 invalid user-pw
Retrieve Sentence   /get            POST            user/pw             200 ok | 301 out of tokens | 302 invalid user-pw


"""
from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt

# on cmd: $ export FLASK_APP=app.py | $ flask run

app = Flask(__name__)
api = Api(app)

# ------------------------------------------------------------------------------
# MongoDB Client and API endpoint
# ------------------------------------------------------------------------------
# rem: when defining the client, the database has same name as in the docker-compose
# rem: 27017 is the default port for MongoDB
client = MongoClient("mongodb://db:27017")
db = client.SentencesDatabase  # create a database
# Rem we need a collection of users where we can store their sentences
users = db["Users"]
# sentencesdb["sentences"]  # create the colledtion UserNum

# HELPER FUNCTIONS  ------------------------------------------------------------
def verifyPw(username, password):
    hashed_pw = users.find({
        'Username': username
    })[0]['Password']

    if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
        return True
    else:
        return False

def countTokens(username):
    tokens = users.find({
        'Username': username
    })[0]['Tokens']
    return tokens

# Need a class in the api to support user registration
class Register(Resource):
    # function that handles user registration:
    def post(self):
        # get data posted by the user
        postedData = request.get_json()

        # get the data
        # rem, need to include validation of posted data, ie:
        #    if 'username' not in postedData or 'password' not in postedData... etc
        username = postedData['username']  # get user
        password = postedData['password']  # get pw
        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())  # hash the pw, make sure it's utf-8

        # Store username and pw into the database
        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Sentence": "",  # initialize with empty sentence
            "Tokens": 6
        })

        # return message to user who is registering
        # -- in future, may want to handle user case where user tries to sign up twice with same info
        returnJSON = {
            "status": 200,
            "msg": "You successfully signed up for the API"
        }
        return jsonify(returnJSON)

        # once you get password, you want to hash & salt it to provide encryption layer
        # hash(password + salt) = asdoiuawerncvoiup1234585aewrn
        # idea is that you need the password to produce encryption, but if you have
        # the encryption, you can't divine the password...
        # so, store the hash, and when the user logs in, you hash the password and see if it
        # matches the stored hash...so don't store the password, just store the hash....
        #
        # to provide the hashing, we'll use PY-BCRYPT, which is a Python wrapper of OpenBSD's Blowfish
        # password hashing code (a python library that allows us to hash a function):
        # https://www.mindrot.org/projects/py-bcrypt

class Store(Resource):
    def post(self):
        # get posted data
        postedData = request.get_json()

        # read the data
        username = postedData['username']
        password = postedData['password']
        sentence = postedData['sentence']

        # verify that the username-pw match
        correct_pw = verifyPw(username, password)

        if not correct_pw:
            returnJSON = {
                'status': 302
            }
            return jsonify(returnJSON)

        # verify that user has enough tokens left
        num_tokens = countTokens(username)
        if num_tokens <= 0:
            returnJSON = {
                'status': 301
            }
            return jsonify(returnJSON)

        # if user-pw match and there are enough tokens,
        # store the sentence, take one token away, and return 200 ok
        users.update(
            { 'Username': username },  # selection criteria is username
            { '$set':{
                'Sentence': sentence,  # update sentence to be the passed-in sentence
                'Tokens': num_tokens-1  # take away a token
                }
            }
        )

        returnJSON = {
            'status': 200,
            'msg': 'Sentence saved successfully'
        }
        return jsonify(returnJSON)

class Get(Resource):
    def post(self):
        # get requested data
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]

        # verify that the username-pw match
        correct_pw = verifyPw(username, password)

        if not correct_pw:
            returnJSON = {
                'status': 302
            }
            return jsonify(returnJSON)

        # verify that user has enough tokens left
        num_tokens = countTokens(username)
        if num_tokens <= 0:
            returnJSON = {
                'status': 301
            }
            return jsonify(returnJSON)

        # make the user pay
        users.update(
            { 'Username': username },  # selection criteria is username
            { '$set':{
                'Tokens': num_tokens-1  # take away a token
                }
            }
        )

        # return the requested sentence
        sentence = users.find({
            'Username': username
        })[0]['Sentence']

        returnJSON = {
            'status': 200,
            'sentence': sentence
        }

        return jsonify(returnJSON)

# add resources to api  --------------------------------------------------------
api.add_resource(Register, '/register')
api.add_resource(Store, '/store')
api.add_resource(Get, '/get')

if __name__=="__main__":
    app.run(host='0.0.0.0')

"""
from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient

# on cmd: $ export FLASK_APP=app.py | $ flask run

app = Flask(__name__)
api = Api(app)

# ------------------------------------------------------------------------------
# MongoDB Client and API endpoint
# ------------------------------------------------------------------------------
# rem: when defining the client, the database has same name as in the docker-compose
# rem: 27017 is the default port for MongoDB
client = MongoClient("mongodb://db:27017")
db = client.aNewDB  # create a database
UserNum = db["UserNum"]  # create the colledtion UserNum
UserNum.insert({  # insert a document into the collection
    'num_of_users':0
})

class Visit(Resource):
    def get(self):
        prev_num = UserNum.find({})[0]['num_of_users']
        #prev_num += 1
        new_num = prev_num + 1
        UserNum.update({}, {"$set":{"num_of_users":new_num}})
        return str("Hello, user " + str(new_num))

# ------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------
def getStatusCodeMsg(status_code):
    msgMap = {
        '200': 'Success',
        '301': 'Missing expected parameter',
        '302': 'Division by zero'
    }
    msg = ''
    for key, val in msgMap.items():
        if key == str(status_code):
            msg = val
    return msg

def checkPostedData(postedData, functionName):
    print('checkPostedData()...')
    if(functionName in ('add', 'subtract', 'multiply')):
        if( 'x' not in postedData or 'y' not in postedData ):
            return 301
        else:
            return 200
    if(functionName == 'divide'):
        if( 'x' not in postedData or 'y' not in postedData ):
            return 301
        elif( postedData['y'] == 0 ):
            return 302
        else:
            return 200

# ------------------------------------------------------------------------------
# API
# ------------------------------------------------------------------------------
class Add(Resource):
    def post(self):  # if control is here, then the resource Add was requested via POST
        # step 1: get posted data
        postedData = request.get_json()

        # step 2: verify posted data... if verification fails, then throw error
        status_code = checkPostedData(postedData, 'add')
        if(status_code != 200):
            responseJSON = {
                'Message': getStatusCodeMsg(status_code),
                'Status Code': status_code
            }
            return jsonify(responseJSON)

        # if posted data verifies, then add values
        x = int(postedData['x'])
        y = int(postedData['y'])

        # step 3: create response
        responseJSON = {
            'Message': x+y,
            'Status Code': status_code
        }

        # step 4: return response to caller
        return jsonify(responseJSON)

    def get(self):  # if control is here, then the resource Add was requested using GET
        pass
    def put(self):  # if control is here, then the resource Add was requested using PUT
        pass
    def delete(self):  # if control is here, then the resource Add was requested using DELETE
        pass

class Subtract(Resource):
    def post(self):  # if control is here, then the resource Add was requested via POST
        # step 1: get posted data
        postedData = request.get_json()

        # step 2: verify posted data... if verification fails, then throw error
        status_code = checkPostedData(postedData, 'subtract')
        if(status_code != 200):
            responseJSON = {
                'Message': getStatusCodeMsg(status_code),
                'Status Code': status_code
            }
            return jsonify(responseJSON)

        # if posted data verifies, then add values
        x = int(postedData['x'])
        y = int(postedData['y'])

        # step 3: create response
        responseJSON = {
            'Message': x-y,
            'Status Code': status_code
        }

        # step 4: return response to caller
        return jsonify(responseJSON)

class Multiply(Resource):
    def post(self):  # if control is here, then the resource Add was requested via POST
        # step 1: get posted data
        postedData = request.get_json()

        # step 2: verify posted data... if verification fails, then throw error
        status_code = checkPostedData(postedData, 'multiply')
        if(status_code != 200):
            responseJSON = {
                'Message': getStatusCodeMsg(status_code),
                'Status Code': status_code
            }
            return jsonify(responseJSON)

        # if posted data verifies, then add values
        x = int(postedData['x'])
        y = int(postedData['y'])

        # step 3: create response
        responseJSON = {
            'Message': x*y,
            'Status Code': status_code
        }

        # step 4: return response to caller
        return jsonify(responseJSON)

class Divide(Resource):
    def post(self):  # if control is here, then the resource Add was requested via POST
        # step 1: get posted data
        postedData = request.get_json()

        # step 2: verify posted data... if verification fails, then throw error
        status_code = checkPostedData(postedData, 'divide')
        if(status_code != 200):
            responseJSON = {
                'Message': getStatusCodeMsg(status_code),
                'Status Code': status_code
            }
            return jsonify(responseJSON)

        # if posted data verifies, then add values
        x = int(postedData['x'])
        y = int(postedData['y'])

        # step 3: create response
        responseJSON = {
            'Message': x/y,
            'Status Code': status_code
        }

        # step 4: return response to caller
        return jsonify(responseJSON)

# API ROUTES  ------------------------------------------------------------------
api.add_resource(Add, "/add")  # add resource and listening endpoint
api.add_resource(Subtract, "/subtract")  # add resource and listening endpoint
api.add_resource(Multiply, "/multiply")  # add resource and listening endpoint
api.add_resource(Divide, "/divide")  # add resource and listening endpoint
api.add_resource(Visit, "/hello")  # add resource and listening endpoint

# ------------------------------------------------------------------------------
# APP
# ------------------------------------------------------------------------------
# URL ROUTES  ------------------------------------------------------------------
@app.route('/')
def home():
    page = '<h2>Flask App</h2>'
    return(page)

@app.route('/add_two_nums', methods=["POST"])
def add_two_nums():
    dataDict = request.get_json()  # get posted data
    if 'y' not in dataDict:return('ERROR', 305)  # throw error if no x in posted data
    if 'x' not in dataDict:return('ERROR', 305)  # throw error if no y in posted data
    x = dataDict['x']  # parse out x value
    y = dataDict['y']  # parse out y value
    z = x + y  # add the posted values
    returnJSON = { "z":z }  # prepare a JSON response
    return jsonify(returnJSON), 200  # return JSON response with success flag

# rem run app at local host dns 0.0.0.0

if __name__=="__main__":
    app.run()
"""
