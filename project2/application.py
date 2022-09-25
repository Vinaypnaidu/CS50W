import os

from collections import deque

from flask import Flask, render_template, session, request, redirect
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from functools import wraps

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("username") is None:
            return redirect("/signin")
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.config["SECRET_KEY"] = "vinay"
socketio = SocketIO(app)

channelsCreated = []

usersLogged = []

channelsMessages = dict()

@app.route("/")
@login_required
def index():

    return render_template("index.html", channels=channelsCreated)

@app.route("/signin", methods=['GET','POST'])
def signin():

    session.clear()

    username = request.form.get("username")

    if request.method == "POST":

        if len(username) < 1 or username is '':
            return "Username cant be empty!"

        if username in usersLogged:
            return "That username already exists!"

        usersLogged.append(username)

        session['username'] = username

        session.permanent = True

        return redirect("/")
    else:
        return render_template("signin.html")

@app.route("/logout", methods=['GET'])
def logout():

    try:
        usersLogged.remove(session['username'])
    except ValueError:
        pass

    session.clear()

    return redirect("/")

@app.route("/create", methods=['GET','POST'])
def create():

    newChannel = request.form.get("channel")

    if request.method == "POST":

        if newChannel in channelsCreated:
            return render_template("error.html", message="that channel already exists!")

        channelsCreated.append(newChannel)


        channelsMessages[newChannel] = deque()

        return redirect("/channels/" + newChannel)

    else:

        return render_template("create.html", channels = channelsCreated)

@app.route("/channels/<channel>", methods=['GET','POST'])
@login_required
def enter_channel(channel):

    session['current_channel'] = channel

    if request.method == "POST":

        return redirect("/")
    else:
        return render_template("channel.html", channels=channelsCreated, messages=channelsMessages[channel])

@socketio.on("joined", namespace='/')
def joined():

    room = session.get('current_channel')

    join_room(room)

    emit('status', {
        'userJoined': session.get('username'),
        'channel': room,
        'msg': session.get('username') + ' has entered the channel'},
        room=room)

@socketio.on("left", namespace='/')
def left():

    room = session.get('current_channel')

    leave_room(room)

    emit('status', {
        'msg': session.get('username') + ' has left the channel'},
        room=room)

@socketio.on('send message')
def send_msg(msg, timestamp):

    room = session.get('current_channel')

    if len(channelsMessages[room]) > 100:
        channelsMessages[room].popleft()

    channelsMessages[room].append([timestamp, session.get('username'), msg])

    emit('announce message', {
        'user': session.get('username'),
        'timestamp': timestamp,
        'msg': msg},
        room=room)