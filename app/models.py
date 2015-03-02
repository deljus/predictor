from app import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    task = db.Column(db.Integer)

    def __repr__(self):
        return '<User %r>' % (self.nickname)