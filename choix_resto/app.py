import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g
import random
import datetime

DATABASE = 'cafes.db'

app = Flask(__name__)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def insert_cafe(name, url):
    db = get_db()
    db.execute('INSERT INTO cafes (name, url) VALUES (?, ?)', (name, url))
    db.commit()

def update_cafe(cafe_id, name, url):
    db = get_db()
    db.execute('UPDATE cafes SET name=?, url=? WHERE id=?', (name, url, cafe_id))
    db.commit()

def delete_cafe(cafe_id):
    db = get_db()
    db.execute('DELETE FROM cafes WHERE id=?', (cafe_id,))
    db.commit()

def mark_visited(cafe_id):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db = get_db()
    db.execute('UPDATE cafes SET last_visited=? WHERE id=?', (timestamp, cafe_id))
    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    selected_cafe = None
    if request.method == 'POST':
        cafe_name = request.form['cafe_name']
        cafe_url = request.form['cafe_url']
        insert_cafe(cafe_name, cafe_url)
        return redirect(url_for('index'))
    else:
        cafes = query_db('SELECT *, last_visited > strftime("%Y-%m-%d %H:%M:%S", "now", "-7 days") as visited_this_week FROM cafes')
        return render_template('index.html', cafes=cafes, selected_cafe=selected_cafe)


@app.route('/get-random-cafe', methods=['POST'])
def get_random_cafe():
    one_week_ago = (datetime.datetime.now() - datetime.timedelta(weeks=1)).strftime('%Y-%m-%d %H:%M:%S')
    available_cafes = query_db("SELECT * FROM cafes WHERE last_visited IS NULL OR last_visited < ?", (one_week_ago,))
    
    if not available_cafes:
        return redirect(url_for('index'))

    selected_cafe = random.choice(available_cafes)
    mark_visited(selected_cafe['id'])
    cafes = query_db('SELECT *, last_visited > strftime("%Y-%m-%d %H:%M:%S", "now", "-7 days") as visited_this_week FROM cafes')
    return render_template('index.html', cafes=cafes, selected_cafe=selected_cafe)


@app.route('/mark-visited/<int:cafe_id>', methods=['POST'])
def mark_visited_route(cafe_id):
    mark_visited(cafe_id)
    return redirect(url_for('index'))

@app.route('/update-cafe/<int:cafe_id>', methods=['POST'])
def update_cafe_route(cafe_id):
    cafe_name = request.form['cafe_name']
    cafe_url = request.form['cafe_url']
    update_cafe(cafe_id, cafe_name, cafe_url)
    return redirect(url_for('index'))

@app.route('/delete-cafe/<int:cafe_id>', methods=['POST'])
def delete_cafe_route(cafe_id):
    delete_cafe(cafe_id)
    return redirect(url_for('index'))


if __name__ == '__main__':
    try:
        init_db()
    except sqlite3.OperationalError:
        pass
    app.run(debug=True)
