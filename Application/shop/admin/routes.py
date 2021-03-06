from flask import render_template, session, request, redirect, url_for, flash
from flask_login import logout_user
from decimal import Decimal
from shop import app, db, login_manager
from .forms import RegistrationForm, LoginForm, StaffRegistrationForm, Addsupplier, Addwarehouse
from .models import Customer, Staff, Supplier, Warehouse, Product, Category, Orders, CreditCard, Stock, AddStock, SupplierItem, ProductPrice, Availability, OrderItem
from .state import state_list
import os

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/admin/<int:id>', methods = ['GET','POST'])
def admin(id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    staff = Staff.query.get_or_404(id)
    products = Product.query.order_by(Product.product_name.asc()).all()
    try:
        if request.method == 'POST':
            keyword = request.form.get('keyword')
            if (Product.query.msearch(keyword, fields = ['product_name']).first() is None):
                flash(f'No relevant product is found', 'danger')
            else:
                products = Product.query.msearch(keyword, fields = ['product_name']).order_by(Product.product_name.asc()).all()
    except Exception as e:
        print (e)
        flash(f'No relevant product is found', 'danger')
    return render_template('admin/index.html', title = 'Admin Page', products = products, staff = staff)

## Build a route for registering a staff account ##

@app.route('/staff_register', methods=['GET', 'POST'])
def staff_register():
    form = StaffRegistrationForm(request.form)
    try:
        if request.method == 'POST' and form.validate():
            staff = Staff(first_name = form.first_name.data, last_name = form.last_name.data,
                        a_line_one= form.a_line_one.data, a_line_two = form.a_line_two.data,
                        a_city = form.a_city.data, a_state = form.a_state.data,
                        a_zipcode = form.a_zipcode.data, phone = form.phone.data, email = form.email.data, 
                        salary = form.salary.data, job_title = form.job_title.data)
            if (Staff.query.filter_by(email = staff.email).first() is not None):
                flash(f'This email already exists. Please register with another email', 'danger')
            else:
                db.session.add(staff)
                db.session.commit()
                flash(f'Welcome {form.first_name.data}! Your staff account is created', 'success')
                return redirect(url_for('staff_login'))
    except Exception as e:
        print(e)
        flash(f'Fails to register.', 'danger')
    return render_template('admin/register.html', title = 'Staff Registeration', form=form)

## Build a route for staff account login##

@app.route('/staff_login', methods=['GET', 'POST'])
def staff_login():
    form = LoginForm(request.form)
    try: 
        if request.method == 'POST' and form.validate():
            staff = Staff.query.filter_by(first_name = form.first_name.data).first()
            if staff and staff.email == form.email.data:
                session['email'] = form.email.data
                flash(f'Welcome {form.first_name.data}. You are logged-in.', 'success')
                return redirect(request.args.get('next') or url_for('admin', id = staff.staff_id))
            else:
                flash(f'Wrong email. Please try again.', 'danger')
    except Exception as e:
        print(e)
        flash(f'Problem occurs during login.', 'danger')
    return render_template('admin/login.html', title = 'Staff Login Page', form=form)

@app.route('/logout')
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('home'))

## Build a route to Delete Customer ##
## Build a route to view Customers' info ##

@app.route('/customer_list/<int:id>', methods = ['GET', 'POST'])
def customer_list(id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    staff = Staff.query.get_or_404(id)
    customers = Customer.query.all()
    try:
        if request.method == 'POST':
            keyword = request.form.get('keyword')
            if (Customer.query.msearch(keyword, fields = ['first_name', 'last_name']).first() is None):
                flash(f'No relevant customer is found', 'danger')
            else:
                customers = Customer.query.msearch(keyword, fields = ['first_name', 'last_name']).all()
    except Exception as e:
        print (e)
        flash(f'No relevant customer is found', 'danger')
    return render_template('admin/customer_list.html', title = 'Customer List Page', customers = customers, staff = staff)

## Build a route to Delete Customer ##

@app.route('/deletecustomer/<int:id>/<int:customer_id>', methods=['POST'])
def deletecustomer(id, customer_id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    staff = Staff.query.get_or_404(id)
    customers = Customer.query.all()
    customer = Customer.query.get_or_404(customer_id)
    try:
        if request.method == "POST":
            db.session.delete(customer)
            db.session.commit()
            flash(f'This customer {customer.first_name} {customer.last_name} was deleted.', 'success')
            return redirect(url_for('customer_list', id = id))
    except Exception as e:
        print(e)
        flash(f'Cannot delete the customer.','danger')
    return render_template('admin/customer_list.html', title = 'Customer List Page', staff = staff, customers = customers)

## Build a route for staff to Query/Modify Customer info AND process orders ##
## The account balance will automatically change since the theorder finished by (paid_total) ##

@app.route('/order_list/<int:id>', methods = ['GET', 'POST'])
def order_list(id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    staff = Staff.query.get_or_404(id)    
    orders = Orders.query.all()
    try: 
        if request.method == 'POST':
            updatestock = OrderItem.query.filter_by(order_id = request.form.get('order_id')).all()
            for item in updatestock:
                product = Stock.query.filter_by(product_id = item.product_id).first()
                product.item_quantity -= int(item.quantity)
                warehouse = Warehouse.query.filter_by(warehouse_id = product.warehouse_id).first()
                product_info = Product.query.filter_by(product_id = item.product_id).first()
                warehouse.capacity_used -= Decimal(item.quantity*product_info.size)
            updateorder = Orders.query.filter_by(order_id = request.form.get('order_id')).first()
            updateorder.status = 'received'
            customer = Customer.query.filter_by(customer_id = updateorder.customer_id).first()
            customer.paid_total += updateorder.ordering_total
            db.session.commit()
            flash(f'The order status is changed to "received".', 'success')
    except Exception as e:
        print(e)
        flash(f'Fails to change order status', 'danger')
    return render_template('admin/order_list.html', title = 'Order List Page', staff = staff, orders = orders)

## Build a route to Delete Customer info ##

@app.route('/deletecsutomer/<int:id>/<int:order_id>', methods=["POST"])
def deleteorder(id, order_id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    staff = Staff.query.get_or_404(id)
    orders = Orders.query.all()
    order = Orders.query.get_or_404(order_id)
    try:
        if request.method == "POST":
            db.session.delete(order)
            db.session.commit()
            flash(f'This order {order.order_id} was deleted.', 'success')
            return redirect(url_for('order_list', id = id))
    except Exception as e:
        print(e)
        flash(f'Cannot delete the order.','danger')
    return render_template('admin/order_list.html', title = 'Order List Page', staff = staff, orders = orders)

## Build a route to Query supplier list ##

@app.route('/suppliers/<int:id>')
def suppliers(id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    staff = Staff.query.get_or_404(id)
    suppliers = Supplier.query.all()
    return render_template('admin/supplier.html', title = 'Supplier Page', suppliers = suppliers, staff = staff)

## Build a route to Add supplier info ##

@app.route('/addsupplier/<int:id>', methods=['GET', 'POST'])
def addsupplier(id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    staff = Staff.query.get_or_404(id)
    try:
        form = Addsupplier(request.form)
        if request.method == 'POST':
            supplier = Supplier(name = form.name.data, phone = form.phone.data, email = form.email.data, 
                        a_line_one = form.a_line_one.data, a_line_two = form.a_line_two.data, a_city = form.a_city.data,
                        a_state = form.a_state.data, a_zipcode = form.a_zipcode.data)
            db.session.add(supplier)
            db.session.commit()
            flash(f'Supplier {form.name.data} is added to your database.', 'success')
            return redirect(url_for('suppliers', id = id))
    except Exception as e:
        print(e)
        flash(f'Fails to add supplier', 'danger')
    return render_template('admin/addsupplier.html', title = "Add Supplier Page", form = form, staff = staff)

## Build a route to Query supplier info ##

@app.route('/supplier_details/<int:id>/<int:supplier_id>', methods=['GET', 'POST'])
def supplier_details(id, supplier_id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('login'))
    staff = Staff.query.get_or_404(id)
    supplier = Supplier.query.get_or_404(supplier_id)
    return render_template('supplier/supplier_details.html', staff = staff, supplier = supplier)

## Build a route to Modify suppliers info ##

@app.route('/updatesupplier/<int:id>/<int:supplier_id>', methods=['GET', 'POST'])
def updatesupplier(id, supplier_id):
    if 'email' not in session:
        flash(f'Plese login first','danger')
    staff = Staff.query.get_or_404(id)
    supplier = Supplier.query.get_or_404(supplier_id)
    try:
        form = Addsupplier(request.form)
        if request.method =="POST":
            supplier.name = form.name.data
            supplier.phone = form.phone.data
            supplier.email = form.email.data
            supplier.a_line_one = form.a_line_one.data
            supplier.a_line_two = form.a_line_two.data
            supplier.a_city = form.a_city.data
            supplier.a_state = form.a_state.data
            supplier.a_zipcode = form.a_zipcode.data
            flash(f'This Supplier {form.name.data} has been updated', 'success')
            db.session.commit()
            return redirect(url_for('suppliers', id = id))
        form.name.data = supplier.name
        form.phone.data = supplier.phone
        form.email.data = supplier.email
        form.a_line_one.data = supplier.a_line_one
        form.a_line_two.data = supplier.a_line_two
        form.a_city.data = supplier.a_city
        form.a_state.data = supplier.a_state
        form.a_zipcode.data = supplier.a_zipcode
    except Exception as e:
        print(e)
        flash(f'Fails to update supplier', 'danger')
    return render_template('admin/updatesupplier.html', title = "Update Supplier Page", staff = staff, form = form, supplier=supplier)

## Build a route to delete supplier info ##

@app.route('/deletesupplier/<int:id>/<int:supplier_id>', methods=["POST"])
def deletesupplier(id, supplier_id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    staff = Staff.query.get_or_404(id)
    suppliers = Supplier.query.all()
    supplier = Supplier.query.get_or_404(supplier_id)
    try:
        if request.method == "POST":
            db.session.delete(supplier)
            db.session.commit()
            flash(f'This supplier {supplier.name} was deleted.', 'success')
            return redirect(url_for('suppliers', id = id))
    except Exception as e:
        print(e)
        flash(f'Cannot delete the supplier.','danger')
    return render_template('admin/supplier.html', title = 'Supplier Page', staff = staff, suppliers = suppliers)

## Build a route to query warehouse list AND check the storage limits ##

@app.route('/warehouses/<int:id>')
def warehouses(id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    staff = Staff.query.get_or_404(id)
    warehouses = Warehouse.query.all()
    return render_template('admin/warehouse.html', title = 'Warehouse Page', warehouses = warehouses, staff = staff)

## Build a route to add warehouse list ##

@app.route('/addwarehouse/<int:id>', methods=['GET', 'POST'])
def addwarehouse(id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    staff = Staff.query.get_or_404(id)
    try: 
        form = Addwarehouse(request.form)
        if request.method == 'POST':
            warehouse = Warehouse(name = form.name.data, a_line_one = form.a_line_one.data,
                        a_line_two = form.a_line_two.data, a_city = form.a_city.data,
                        a_state = form.a_state.data, a_zipcode = form.a_zipcode.data,
                        capacity = form.capacity.data)
            db.session.add(warehouse)
            db.session.commit()
            flash(f'Warehouse {form.name.data} is added to your database.', 'success')
            return redirect(url_for('warehouses', id = id))
    except Exception as e:
        print(e)
        flash(f'Fails to add warehouse', 'danger')
    return render_template('admin/addwarehouse.html', title = "Add Warehouse Page", form = form, staff = staff)

## Build a route to query warehouse info ##

@app.route('/warehouse_details/<int:id>/<int:warehouse_id>', methods=['GET', 'POST'])
def warehouse_details(id, warehouse_id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('login'))
    staff = Staff.query.get_or_404(id)
    warehouse = Warehouse.query.get_or_404(id)
    return render_template('warehouse/warehouse_details.html', staff = staff, warehouse = warehouse)


## Build a route to modify warehouse info ##

@app.route('/updatewarehouse/<int:id>/<int:warehouse_id>', methods=['GET', 'POST'])
def updatewarehouse(id, warehouse_id):
    if 'email' not in session:
        flash(f'Plese login first','danger')
    staff = Staff.query.get_or_404(id)
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    try: 
        form = Addwarehouse(request.form)
        if request.method =="POST":
            warehouse.name = form.name.data
            warehouse.a_line_one = form.a_line_one.data
            warehouse.a_line_two = form.a_line_two.data
            warehouse.a_city = form.a_city.data
            warehouse.a_state = form.a_state.data
            warehouse.a_zipcode = form.a_zipcode.data
            warehouse.capacity = form.capacity.data
            flash(f'This warehouse {form.name.data} has been updated', 'success')
            db.session.commit()
            return redirect(url_for('warehouses', id = id))
        form.name.data = warehouse.name
        form.a_line_one.data = warehouse.a_line_one 
        form.a_line_two.data = warehouse.a_line_two
        form.a_city.data = warehouse.a_city
        form.a_state.data = warehouse.a_state
        form.a_zipcode.data = warehouse.a_zipcode
        form.capacity.data = warehouse.capacity
    except Exception as e:
        print(e)
        flash(f'Fails to update warehouse', 'danger')
    return render_template('admin/updatewarehouse.html', title = "Update Warehouse Page", staff = staff, form = form, warehouse = warehouse)

## Build a route to delete warehouse ##

@app.route('/deletewarehouse/<int:id>/<int:warehouse_id>', methods=["POST"])
def deletewarehouse(id, warehouse_id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    staff = Staff.query.get_or_404(id)
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    try: 
        if request.method == "POST":
            db.session.delete(warehouse)
            db.session.commit()
            flash(f'This warehouse {warehouse.name} was deleted.', 'success')
            return redirect(url_for('warehouses', id = id))
    except Exception as e:
        print(e)
        flash(f'Cannot delete the warehouse.','danger')
    return render_template('admin/warehouse.html', title = 'Warehouse Page', warehouses = warehouses, staff = staff)

## Build a route to add/modify stock/ Update availability of product in stock/ check the storage limits ##

@app.route('/addstock/<int:id>', methods = ['GET', 'POST'])
def addstock(id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    staff = Staff.query.get_or_404(id)
    try: 
        warehouses = Warehouse.query.all()
        products = Product.query.all()
        if request.method == "POST":
            stock = request.form.get('product_id')
            quantity = request.form.get('quantity')
            product = Product.query.filter_by(product_id = stock).first()
            addstock = AddStock(staff_id = request.form.get('staff_id'), product_id = stock,
                                warehouse_id = request.form.get('warehouse_id'), add_quantity = quantity,
                                add_size = int(quantity)*float(product.size))
            updatewh = Warehouse.query.get_or_404(addstock.warehouse_id)
            if (updatewh.capacity_remained < Decimal(addstock.add_size)):
                flash(f'Warehouse {updatewh.name} does not have enough space for new stock','danger')
                return redirect(url_for('addstock',id = id))
            elif (Stock.query.filter_by(product_id = addstock.product_id).filter_by(warehouse_id = addstock.warehouse_id).first() is None):
                newstock = Stock(product_id = addstock.product_id, warehouse_id = addstock.warehouse_id, 
                                item_quantity = quantity, size_total = int(quantity)*float(product.size))
                db.session.add(newstock)
                db.session.commit()
                db.session.add(addstock)
                updatewh.capacity_used += Decimal(addstock.add_size)
                newavail = Availability(product_id = addstock.product_id, warehouse_id = addstock.warehouse_id, item_quantity = quantity)
                db.session.add(newavail)
                db.session.commit()
                flash(f'New item {product.product_name} is added into Stock.', 'success')
                return redirect(url_for('addstock',id = id))
            else:
                updatestock = Stock.query.filter_by(product_id = addstock.product_id).filter_by(warehouse_id = addstock.warehouse_id).first()
                updatestock.item_quantity += int(addstock.add_quantity)
                updatestock.size_total += Decimal(addstock.add_size)
                upaddstock = AddStock.query.filter_by(product_id = addstock.product_id).filter_by(warehouse_id = addstock.warehouse_id).first()
                upaddstock.add_quantity = addstock.add_quantity
                upaddstock.add_size = addstock.add_size
                updatewh = Warehouse.query.get_or_404(addstock.warehouse_id)
                updatewh.capacity_used += Decimal(addstock.add_size)
                updateavail = Availability.query.filter_by(product_id = addstock.product_id).filter_by(warehouse_id = addstock.warehouse_id).first()
                updateavail.item_quantity += int(quantity)
                db.session.commit()
                flash(f'More stock {product.product_name} is added.', 'success')
                return redirect(url_for('addstock',id = id))
    except Exception as e:
        print(e)
        flash(f'Somethings went wrong while adding stock','danger')
        return redirect(url_for('addstock', id = id))
    return render_template('admin/addstock.html', title = "Add Stock Page", staff = staff, warehouses = warehouses, products = products)

## Build a route to set a specific supplier price ##

@app.route('/supplierprice/<int:id>', methods = ['GET', 'POST'])
def supplierprice(id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    try: 
        staff = Staff.query.get_or_404(id)
        suppliers = Supplier.query.all()
        products = Product.query.all()
        if request.method == "POST":
            newprice = SupplierItem(supplier_id = request.form.get('supplier_id'),product_id = request.form.get('product_id'),
                                    supplier_price = request.form.get('newprice'))
            if (SupplierItem.query.filter_by(supplier_id = newprice.supplier_id).filter_by(product_id = newprice.product_id).first() is None):
                db.session.add(newprice)
                db.session.commit()
            else:
                updateprice = SupplierItem.query.filter_by(supplier_id = newprice.supplier_id).filter_by(product_id = newprice.product_id).first()
                updateprice.supplier_price = newprice.supplier_price
                db.session.commit()
            flash(f'New price is updated.', 'success')
    except Exception as e:
        print(e)
        flash(f'Somethings went wrong while updating supplier price','danger')
        return redirect(url_for('supplierprice', id = id))
    return render_template('admin/supplier_newprice.html', title = "Supplier Price Page", staff = staff, suppliers = suppliers, products = products)

## Build a route to set/modify product price by delivery state ##

@app.route('/pricebystate/<int:id>', methods = ['GET', 'POST'])
def stateprice(id):
    if 'email' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('home'))
    try: 
        staff = Staff.query.get_or_404(id)
        products = Product.query.all()
        states = state_list
        if request.method == "POST":
            stateprice = ProductPrice(product_id = request.form.get('product_id'),delivery_state = request.form.get('state'),
                                    price = request.form.get('newprice'))
            if (stateprice.price == '0'):
                if (ProductPrice.query.filter_by(product_id = stateprice.product_id).filter_by(delivery_state = stateprice.delivery_state).first() is not None):
                    deleteprice = ProductPrice.query.filter_by(product_id = stateprice.product_id).filter_by(delivery_state = stateprice.delivery_state).first()
                    db.session.delete(deleteprice)
                    db.session.commit()
                    flash(f'This price record is deleted.', 'success')
                return redirect(url_for('stateprice', id = id))
            elif (ProductPrice.query.filter_by(product_id = stateprice.product_id).filter_by(delivery_state = stateprice.delivery_state).first() is None):
                db.session.add(stateprice)
                db.session.commit()
                flash(f'New price is added.', 'success')
            else:
                updateprice = ProductPrice.query.filter_by(product_id = stateprice.product_id).filter_by(delivery_state = stateprice.delivery_state).first()
                updateprice.price = stateprice.price
                db.session.commit()
                flash(f'New price is updated.', 'success')
    except Exception as e:
        print(e)
        flash(f'Somethings went wrong while updating state price','danger')
        return redirect(url_for('stateprice', id = id))
    return render_template('admin/stateprice.html', title = "State Price Page", staff = staff, states = states, products = products)
