import os
from dataclasses import dataclass
from flask import Flask, jsonify, Response, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, date, timezone
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import DeclarativeMeta

import uuid
import json

actions = ["Place_Block", "Break_Block", "World_Edit", "Debug_Stick", "Rollback"]

reverseActions = ["Break_Block", "Place_Block", "Break_BlockWE", "Place_BlockWE", "Debug_Stick", "Container_Remove", "Container_Add"]

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.secret_key = "67yu7uy6h j7"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app)

# Source - https://stackoverflow.com/a
# Posted by Sasha B, modified by community. See post 'Timeline' for change history
# Retrieved 2026-01-05, License - CC BY-SA 4.0

# Modified by TealishGreen

class AlchemyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    json.dumps(data) # this will fail on non-encodable values, like other classes
                    fields[field] = data
                except TypeError:
                        if isinstance(data, datetime):
                            json.dumps(data.timestamp())
                            fields[field] = data.timestamp()
                        else:
                            fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)

@dataclass
class Block(db.Model):
    locationX = db.Column(db.Integer, nullable=False)
    locationY = db.Column(db.Integer, nullable=False)
    locationZ = db.Column(db.Integer, nullable=False)
    material = db.Column(db.String(50), nullable=False)
    state = db.Column(db.Text, nullable=False)
    modifier = db.Column(db.String(36), nullable=False)
    action = db.Column(db.String(15), nullable=False)
    modifiedAt = db.Column(db.DateTime(timezone=False),
                           server_default=func.now())
    id = db.Column(db.String(30), primary_key=True)

    def __repr__(self):
        return f'<Block {self.locationX} {self.locationY} {self.locationZ} {self.modifier} {self.modifiedAt} {self.id}>'

    def to_dict(self):
        return {
            "id": self.id,
            "locationX": self.locationX,
            "locationY": self.locationY,
            "locationZ": self.locationZ,
            "material": self.material,
            "state": self.state,
            "modifier": self.modifier,
            "action": self.action,
            "modifiedAt": self.modifiedAt.isoformat()
        }


@app.route('/')
def index():
    return "y'all need to stop with this softcoding stuff: You're generally referring to removing repeated code – and yes, this a good thing, normally. However, there are two issues with the attitude around this. First, not every situation mandates this kind of code structure. This is especially true of smaller games made by newer developers. We shouldn't avoid adding certain QOL features simply because in a \"properly\" coded game it isn't necessary. This second point doesn't apply specifically to this conversation but I see it coming up frequently so here goes: a lot of people take this way too far. I have seen so many plots where they do crazy things like spawn items on the ground to load information and whatnot. This is not good. Don't sacrifice code legibility and efficiency simply because they believe it makes coding experience easier. There is a delicate balance between well designed, easy to maintain, and efficient code. Softcoding is not always the way to achieve this balance. So please, just think about the systems you're designing and whether or not anything is actually improved. tl;dr elitism through \"better practice\" / softcoding doesn't help, and often it isn't the right answer"

@app.route('/version/')
def version():
    return Response(json.dumps("2.0"), mimetype='application/json')

@app.route('/get/<int:x>/<int:y>/<int:z>/')
def student(x, y, z):
    student = Block.query.filter(Block.locationX == x, Block.locationY == y, Block.locationZ == z).first()
    print(student)
    return Response(json.dumps(student, cls=AlchemyEncoder), mimetype='application/json')


@app.route('/getbefore/<int:date>')
def getbefore(date):
    blocks = Block.query.filter(Block.modifiedAt <= datetime.fromtimestamp(date, timezone.utc)).all()
    print(blocks)
    return Response(json.dumps(blocks, cls=AlchemyEncoder), mimetype='application/json')

@app.route('/getrollbackdata/<int:date>/<modifier>', methods=["GET"])
def getrollbackdata(date, modifier):
    dt = datetime.fromtimestamp(date, timezone.utc)
    print(Block.query.filter(
        Block.modifiedAt >= dt,
        Block.modifier == modifier
    ).all())
    blocks = Block.query.filter(
        Block.modifiedAt >= dt,
        Block.modifier == modifier
    ).all()

    return Repsonse(json.dumps(blocks, cls=AlchemyEncoder), mimetype='application/json')
@app.route('/delrollbackdata/<int:date>/<modifier>', methods=["DELETE"])
def delafter(date, modifier):
    db.session.execute(
        db.delete(Block).filter(Block.modifiedAt >= datetime.utcfromtimestamp(date), Block.modifier == modifier)
    )
    db.session.commit()
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

@app.route('/deleteold', methods=['DELETE'])
def deleteold():
    db.session.execute(
        db.delete(Block).filter(Block.modifiedAt <= date.today() - timedelta(2))
    )
    db.session.commit()
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

@app.route('/create/', methods=['POST'])
def create():
    data = request.get_json()
    print(data)
    new_blocks = [
        Block(
            id=str(uuid.uuid4()),
            locationX=int(json.loads(item)['x']),
            locationY=int(json.loads(item)['y']),
            locationZ=int(json.loads(item)['z']),
            material=json.loads(item)['material'],
            state=json.loads(item)['state'],
            modifier=json.loads(item)['modifier'],
            action=actions[int(json.loads(item)['action'])],
            modifiedAt=datetime.utcfromtimestamp(float(json.loads(item)['date']))
        ) for item in data
    ]

    try:
        db.session.add_all(new_blocks)
        db.session.commit()
    except Exception as e:
        db.session.rollback()  # Always rollback on IntegrityError
        raise e

    return {'you_sent': data}, 200

@app.route("/checkconn")
def checkConn():
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
