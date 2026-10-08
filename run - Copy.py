from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / 'app' / 'templates'),
    static_folder=str(BASE_DIR / 'app' / 'static'),
)
app.secret_key = "ilogic_secret"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(BASE_DIR / 'test.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─── MODELS ───────────────────────────────────────────────────────────────────

class Vehicle(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    vendor_type  = db.Column(db.String(50), default="Direct Customer")
    # Vendor-specific fields
    v_cust_name  = db.Column(db.String(100))
    v_cust_phone = db.Column(db.String(50))
    v_cust_id    = db.Column(db.String(100))
    v_agent_name    = db.Column(db.String(100))
    v_agent_comm    = db.Column(db.String(50))
    v_agent_details = db.Column(db.String(200))
    v_fin_name   = db.Column(db.String(100))
    v_fin_ref    = db.Column(db.String(100))
    v_fin_date   = db.Column(db.String(50))
    v_branch_name  = db.Column(db.String(100))
    v_branch_id    = db.Column(db.String(100))
    v_branch_staff = db.Column(db.String(100))
    # Vehicle fields
    name         = db.Column(db.String(100))
    number       = db.Column(db.String(50))
    owners       = db.Column(db.String(20))
    model        = db.Column(db.String(50))
    regno        = db.Column(db.String(50))
    insurance    = db.Column(db.String(20))
    fc           = db.Column(db.String(50))
    pdate        = db.Column(db.String(30))
    purchase     = db.Column(db.Float, default=0)
    selling      = db.Column(db.Float, default=0)
    status       = db.Column(db.String(20), default="Available")
    notes        = db.Column(db.Text)
    image        = db.Column(db.Text)   # base64 image string

class Repair(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    name       = db.Column(db.String(200))
    cost       = db.Column(db.Float, default=0)

class Sale(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    customer   = db.Column(db.String(100))
    contact    = db.Column(db.String(50))
    amount     = db.Column(db.Float)
    payment    = db.Column(db.String(50))
    date       = db.Column(db.String(30))
    notes      = db.Column(db.Text)

class Expense(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100))
    amount   = db.Column(db.Float, default=0)
    date     = db.Column(db.String(30))
    notes    = db.Column(db.Text)

class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role     = db.Column(db.String(50), default="User")

class StoreSetting(db.Model):
    id      = db.Column(db.Integer, primary_key=True)
    name    = db.Column(db.String(100))
    gst     = db.Column(db.String(100))
    address = db.Column(db.Text)
    phone   = db.Column(db.String(20))
    email   = db.Column(db.String(100))
    city    = db.Column(db.String(100))
    state   = db.Column(db.String(100))
    pincode = db.Column(db.String(10))

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", password="1234", role="Admin"))
        db.session.commit()

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def vehicle_to_dict(v):
    repairs = Repair.query.filter_by(vehicle_id=v.id).all()
    sale = Sale.query.filter_by(vehicle_id=v.id).first()
    return {
        "id": v.id,
        "vendorType": v.vendor_type or "Direct Customer",
        "v_cust_name": v.v_cust_name or "",
        "v_cust_phone": v.v_cust_phone or "",
        "v_cust_id": v.v_cust_id or "",
        "v_agent_name": v.v_agent_name or "",
        "v_agent_comm": v.v_agent_comm or "",
        "v_agent_details": v.v_agent_details or "",
        "v_fin_name": v.v_fin_name or "",
        "v_fin_ref": v.v_fin_ref or "",
        "v_fin_date": v.v_fin_date or "",
        "v_branch_name": v.v_branch_name or "",
        "v_branch_id": v.v_branch_id or "",
        "v_branch_staff": v.v_branch_staff or "",
        "name": v.name or "",
        "number": v.number or "",
        "owners": v.owners or "",
        "model": v.model or "",
        "regno": v.regno or "",
        "insurance": v.insurance or "Live",
        "fc": v.fc or "",
        "pdate": v.pdate or "",
        "purchase": v.purchase or 0,
        "selling": v.selling or 0,
        "status": v.status or "Available",
        "notes": v.notes or "",
        "image": v.image or "",
        "repairs": [{"id": r.id, "name": r.name, "cost": r.cost} for r in repairs],
        "sale": {"customer": sale.customer, "amount": sale.amount, "date": sale.date,
                 "contact": sale.contact, "payment": sale.payment, "notes": sale.notes} if sale else None
    }

# ─── AUTH ROUTES ──────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username'),
                                    password=request.form.get('password')).first()
        if user:
            session['user'] = user.username
            session['role'] = user.role
            return redirect(url_for('home'))
        flash("Invalid Login ❌")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── PAGE ROUTES ──────────────────────────────────────────────────────────────

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/vehicle')
@app.route('/inventory')
def vehicle():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('add_vehicle.html')

@app.route('/add_vehicle')
def add_vehicle():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('add_vehicle.html')

@app.route('/sales')
def sales():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('sales.html')

@app.route('/expenses')
def expenses():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('Expense.html')

@app.route('/orders')
def orders():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('orders.html')

@app.route('/reports')
def reports():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('reports.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        user = User.query.filter_by(username=session['user']).first()
        cur = request.form.get('current_password')
        new = request.form.get('new_password')
        con = request.form.get('confirm_password')
        if user and user.password == cur:
            if new != con:
                flash("Passwords do not match ❌", "danger")
            else:
                user.password = new
                db.session.commit()
                flash("Password updated ✅", "success")
        else:
            flash("Wrong current password ❌", "danger")
    return render_template('settings.html')

# ─── VEHICLE API ──────────────────────────────────────────────────────────────

@app.route('/api/vehicles')
def api_get_vehicles():
    vendor = request.args.get('vendor', 'All')
    q = Vehicle.query
    if vendor != 'All':
        q = q.filter_by(vendor_type=vendor)
    return jsonify([vehicle_to_dict(v) for v in q.all()])

@app.route('/api/vehicles/<int:vid>')
def api_get_vehicle(vid):
    v = Vehicle.query.get_or_404(vid)
    return jsonify(vehicle_to_dict(v))

@app.route('/api/vehicles', methods=['POST'])
def api_add_vehicle():
    d = request.json
    v = Vehicle(
        vendor_type=d.get('vendorType','Direct Customer'),
        v_cust_name=d.get('v_cust_name',''), v_cust_phone=d.get('v_cust_phone',''), v_cust_id=d.get('v_cust_id',''),
        v_agent_name=d.get('v_agent_name',''), v_agent_comm=d.get('v_agent_comm',''), v_agent_details=d.get('v_agent_details',''),
        v_fin_name=d.get('v_fin_name',''), v_fin_ref=d.get('v_fin_ref',''), v_fin_date=d.get('v_fin_date',''),
        v_branch_name=d.get('v_branch_name',''), v_branch_id=d.get('v_branch_id',''), v_branch_staff=d.get('v_branch_staff',''),
        name=d.get('name',''), number=d.get('number',''), owners=d.get('owners',''),
        model=d.get('model',''), regno=d.get('regno',''), insurance=d.get('insurance','Live'),
        fc=d.get('fc',''), pdate=d.get('pdate',''),
        purchase=float(d.get('purchase') or 0), selling=float(d.get('selling') or 0),
        status=d.get('status','Available'), notes=d.get('notes',''), image=d.get('image','')
    )
    db.session.add(v)
    db.session.flush()
    for r in d.get('repairs', []):
        db.session.add(Repair(vehicle_id=v.id, name=r['name'], cost=float(r.get('cost',0))))
    db.session.commit()
    return jsonify({"status": "success", "id": v.id})

@app.route('/api/vehicles/<int:vid>', methods=['PUT'])
def api_update_vehicle(vid):
    v = Vehicle.query.get_or_404(vid)
    d = request.json
    v.vendor_type=d.get('vendorType', v.vendor_type)
    v.v_cust_name=d.get('v_cust_name',''); v.v_cust_phone=d.get('v_cust_phone',''); v.v_cust_id=d.get('v_cust_id','')
    v.v_agent_name=d.get('v_agent_name',''); v.v_agent_comm=d.get('v_agent_comm',''); v.v_agent_details=d.get('v_agent_details','')
    v.v_fin_name=d.get('v_fin_name',''); v.v_fin_ref=d.get('v_fin_ref',''); v.v_fin_date=d.get('v_fin_date','')
    v.v_branch_name=d.get('v_branch_name',''); v.v_branch_id=d.get('v_branch_id',''); v.v_branch_staff=d.get('v_branch_staff','')
    v.name=d.get('name', v.name); v.number=d.get('number', v.number)
    v.owners=d.get('owners',''); v.model=d.get('model',''); v.regno=d.get('regno','')
    v.insurance=d.get('insurance','Live'); v.fc=d.get('fc',''); v.pdate=d.get('pdate','')
    v.purchase=float(d.get('purchase') or 0); v.selling=float(d.get('selling') or 0)
    v.status=d.get('status', v.status); v.notes=d.get('notes','')
    if d.get('image'):
        v.image = d['image']
    # Update repairs
    Repair.query.filter_by(vehicle_id=vid).delete()
    for r in d.get('repairs', []):
        db.session.add(Repair(vehicle_id=vid, name=r['name'], cost=float(r.get('cost',0))))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/vehicles/<int:vid>', methods=['DELETE'])
def api_delete_vehicle(vid):
    v = Vehicle.query.get_or_404(vid)
    Repair.query.filter_by(vehicle_id=vid).delete()
    Sale.query.filter_by(vehicle_id=vid).delete()
    db.session.delete(v)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/vehicles/<int:vid>/sell', methods=['POST'])
def api_sell_vehicle(vid):
    v = Vehicle.query.get_or_404(vid)
    d = request.json
    # Remove old sale if exists
    Sale.query.filter_by(vehicle_id=vid).delete()
    sale = Sale(
        vehicle_id=vid,
        customer=d.get('customer',''),
        contact=d.get('contact',''),
        amount=float(d.get('amount') or 0),
        payment=d.get('payment','Cash'),
        date=d.get('date',''),
        notes=d.get('notes','')
    )
    v.status = "Sold"
    db.session.add(sale)
    db.session.commit()
    return jsonify({"status": "success"})

# ─── SALES / ORDERS API ───────────────────────────────────────────────────────

@app.route('/api/available_vehicles')
def api_available_vehicles():
    vehicles = Vehicle.query.filter_by(status='Available').all()
    return jsonify([{"id": v.id, "name": v.name, "number": v.number,
                     "selling": v.selling, "purchase": v.purchase,
                     "model": v.model, "image": v.image} for v in vehicles])

@app.route('/api/sold_vehicles')
def api_sold_vehicles():
    vehicles = Vehicle.query.filter_by(status='Sold').all()
    result = []
    for v in vehicles:
        sale = Sale.query.filter_by(vehicle_id=v.id).first()
        repairs = Repair.query.filter_by(vehicle_id=v.id).all()
        repair_cost = sum(r.cost for r in repairs)
        result.append({
            "id": v.id, "name": v.name, "number": v.number,
            "model": v.model, "image": v.image,
            "purchase": v.purchase, "selling": v.selling,
            "repair_cost": repair_cost,
            "sale": {"customer": sale.customer, "amount": sale.amount,
                     "date": sale.date, "contact": sale.contact,
                     "payment": sale.payment} if sale else None
        })
    return jsonify(result)

# ─── EXPENSE API ──────────────────────────────────────────────────────────────

@app.route('/api/expenses')
def api_get_expenses():
    return jsonify([{"id": e.id, "category": e.category, "amount": e.amount,
                     "date": e.date, "notes": e.notes} for e in Expense.query.all()])

@app.route('/api/expenses', methods=['POST'])
def api_add_expense():
    d = request.json
    e = Expense(category=d.get('category',''), amount=float(d.get('amount') or 0),
                date=d.get('date',''), notes=d.get('notes',''))
    db.session.add(e); db.session.commit()
    return jsonify({"status": "success", "id": e.id})

@app.route('/api/expenses/<int:eid>', methods=['PUT'])
def api_update_expense(eid):
    e = Expense.query.get_or_404(eid)
    d = request.json
    e.category=d.get('category', e.category); e.amount=float(d.get('amount') or 0)
    e.date=d.get('date', e.date); e.notes=d.get('notes', e.notes)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/expenses/<int:eid>', methods=['DELETE'])
def api_delete_expense(eid):
    e = Expense.query.get_or_404(eid)
    db.session.delete(e); db.session.commit()
    return jsonify({"status": "success"})

# ─── SETTINGS API ─────────────────────────────────────────────────────────────

@app.route('/api/save_store', methods=['POST'])
def save_store():
    data = request.json
    setting = StoreSetting.query.first() or StoreSetting()
    setting.name=data.get('name',''); setting.gst=data.get('gst','')
    setting.address=data.get('address',''); setting.phone=data.get('phone','')
    setting.email=data.get('email',''); setting.city=data.get('city','')
    setting.state=data.get('state',''); setting.pincode=data.get('pincode','')
    db.session.add(setting); db.session.commit()
    return {"status": "success"}

@app.route('/api/get_store')
def get_store():
    s = StoreSetting.query.first()
    if s:
        return {"name":s.name or "","gst":s.gst or "","address":s.address or "",
                "phone":s.phone or "","email":s.email or "","city":s.city or "",
                "state":s.state or "","pincode":s.pincode or ""}
    return {"name":"","gst":"","address":"","phone":"","email":"","city":"","state":"","pincode":""}

@app.route('/api/get_users')
def get_users():
    return {"users": [{"username": u.username, "role": u.role} for u in User.query.all()]}

@app.route('/api/add_user', methods=['POST'])
def add_user():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return {"status": "error", "message": "User exists"}, 400
    db.session.add(User(username=data['username'], password=data['password'], role=data['role']))
    db.session.commit()
    return {"status": "success"}

@app.route('/api/delete_user/<username>', methods=['DELETE'])
def delete_user(username):
    if username == 'admin':
        return {"status": "error"}, 400
    user = User.query.filter_by(username=username).first()
    db.session.delete(user); db.session.commit()
    return {"status": "success"}

if __name__ == "__main__":
    app.run(debug=True)