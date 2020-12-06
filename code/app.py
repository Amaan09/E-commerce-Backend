from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from flask_pymongo import PyMongo
from flask_cors import CORS, cross_origin
import bcrypt
from bson.json_util import dumps
from bson.objectid import ObjectId 
import json

app = Flask(__name__)
app.secret_key = "secret key"
# app.config["MONGO_URI"] = "mongodb://localhost:27017/shoppers"
app.config["MONGO_URI"] = "mongodb+srv://root:1234@cluster0.olrx5.mongodb.net/shoppers?retryWrites=true&w=majority"
mongo = PyMongo(app)
api = Api(app)
CORS(app)


# Product Routes
class Product(Resource):
    def get(self, id):
        product = mongo.db.products.find_one({'_id': ObjectId(id)})
        res = json.loads(dumps(product))
        return res, 200
    def put(self, id):
        data = request.json
        mongo.db.products.find_one_and_update(
            {
                '_id': ObjectId(id),
            }, 
            {
                '$set': data
            }
        )
        return {'message': 'Details Updated'}, 200
    def delete(self, id):
        mongo.db.products.find_one_and_delete(
            {
                '_id': ObjectId(id),
            }
        )
        return {'message': 'Product Deleted'}, 200

@app.route('/products', methods = ['GET', 'POST'])
def products():
    if request.method == 'GET':
        products = mongo.db.products.find()
        res = dumps(products)
        # x = []
        # for product in products:
        # 	x.append({'name': product['name'], 'price': product['price']})
        return res, 200
    else:
        data = request.json
        name = data['name']
        price = data['price']
        category = data['category']
        imagePath = data['imagePath']
        mongo.db.products.insert(
            {
                'name': name,
                'price': price,
                'category': category,
                'imagePath': imagePath
            }
        )
        return jsonify({'message': 'Product stored successfully'}), 200


# Users Login and signup routes
@app.route('/signup', methods = ['POST'])
def signup():
    data = request.json
    name = data['name']
    email = data['email']
    password = data['password']
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    mongo.db.users.insert_one(
        {
            'name': name,
            'email': email,
            'password': hashed.decode('utf-8'),
            'address': '',
            'state': '',
            'zipCode': '',
            'mobile': ''
        }
    )
    user = mongo.db.users.find({
        'email': email
    })
    for doc in user:
        user_id = doc['_id']
    
    mongo.db.cart.insert({
        'user_id': ObjectId(user_id),
        'products': []
    })
    return jsonify({'message': 'User signedup successfully'}), 200

@app.route('/login', methods = ['POST'])
def login():
    data = request.json
    email = data['email']
    password = data['password']
    user = mongo.db.users.find({'email': email})
    u_email = None
    hashed = None
    for doc in user:
        u_email = doc['email']
        hashed = doc['password']
    if email == u_email and bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8')):
        return jsonify({'message': 'User loggedin successfully'}), 200
    else:
        return jsonify({'message': 'Invalid Credentials'}), 200

@app.route('/update/<id>', methods = ['PUT'])
def update_user(id):
    data = request.json
    mongo.db.users.find_one_and_update(
        {
            '_id': ObjectId(id),
        }, 
        {
            '$set': data
        }
    )
    return {'message': 'Details Updated'}, 200

# Cart Routes
class Cart(Resource):
    def get(self, id):
        cart = mongo.db.cart.aggregate([
            { "$unwind": "$products" },
            { "$lookup": {
                "from": "products",
                "localField": "products.product_id",
                "foreignField": "_id",
                "as": "productObjects"
            }},
            { "$match": {"user_id": ObjectId(id)} },
            { "$unwind": "$productObjects" },
            { "$group": {
                "_id": "$_id",
                "products": { "$push": "$products" },
                "productObjects": { "$push": "$productObjects" }
            }}
        ])
        res = json.loads(dumps(cart))
        return res, 200
    def post(self, id):
        data = request.json
        product_id = data['product_id']
        size = data['size']
        quantity = data['quantity']
        
        cart = mongo.db.cart.find({'user_id': ObjectId(id)})
        
        cart_id = None
        for doc in cart:
            cart_id = doc['_id']
        
        result = mongo.db.cart.update(
            {
                '_id': cart_id,
            }, 
            {
                '$push': {
                    'products': {
                        '$each': [ { 'product_id': ObjectId(product_id), 'size': size, 'quantity': quantity }]
                    }
                }
            }
        );

        return {'message':'Created Successfully'}, 200
    # def put(self, id):
    #     data = request.json
    #     product_id = data['product_id']
    #     quantity = data['quantity']
    #     cart = mongo.db.cart.find({'user_id': ObjectId(id)})
    #     cart_id = None
    #     for doc in cart:
    #         cart_id = doc['_id']
    #     mongo.db.cart.update(
    #         {
    #             '_id': cart_id,
    #             'products.product_id': ObjectId(product_id)
    #         }, 
    #         {
    #             '$set': {'products.$.quantity': quantity}
    #         }
    #     );
    #     return {'message':'Updated Successfully'}, 200
    def put(self, id):
        data = request.json
        product_id = data['product_id']
        cart = mongo.db.cart.find({'user_id': ObjectId(id)})
        cart_id = None
        for doc in cart:
            cart_id = doc['_id']

        mongo.db.cart.update(
            { '_id': cart_id },
            { '$pull': {"products": {'product_id': ObjectId(product_id)}} }
        );
        return {'message': 'Product Deleted'}, 200
    def delete(self, id):
        mongo.db.cart.update(
            {'user_id': ObjectId(id)},
            {'$set': {"products": []}}
        )
        return {'message': 'Products Deleted'}


@app.route('/cart/<id>/count')
def cart_count(id):
    data = request.json
    cart = mongo.db.cart.aggregate([
        {'$match': {'user_id' : ObjectId(id)}}, 
        {'$unwind': "$products"},
        {'$project': {'count':{'$add':1}}},
        {'$group': {'_id': 'null', 'number': {'$sum': "$count" }}}
    ]);
    count = None
    for doc in cart:
        count = doc['number']
    return {'count': count}, 200


# Orders Routes
class Order(Resource):
    def get(self, id):
        orders = mongo.db.orders.find_one({'user_id': ObjectId(id)})
        res = json.loads(dumps(orders))
        return {'orders': res}, 200
    def post(self, id):
        data = request.json
        cart_id = data['cart_id']
        user_id = id
        status = "Not Delivered"
        mongo.db.orders.insert(
            {
                'user_id': ObjectId(user_id),
                'cart_id': ObjectId(cart_id),
                'status': status
            }
        )
        mongo.db.cart.update(
            { '_id': ObjectId(cart_id) },
            { '$pull': {'products': {} }}    
        );
        return {'message': 'Order stored successfully'}, 200
    def put(self, id):
        data = request.json
        mongo.db.orders.find_one_and_update(
            {
                'user_id': ObjectId(id),
            }, 
            {
                '$set': data
            }
        )
        return {'message': 'Details Updated'}, 200
    def delete(self, id):
        mongo.db.orders.find_one_and_delete(
            {
                'user_id': ObjectId(id),
            }
        )
        return {'message': 'Product Deleted'}, 200



api.add_resource(Product, '/products/<id>')
api.add_resource(Cart, '/cart/<id>')
api.add_resource(Order, '/orders/<id>')
app.run(port=5000, debug=True)

