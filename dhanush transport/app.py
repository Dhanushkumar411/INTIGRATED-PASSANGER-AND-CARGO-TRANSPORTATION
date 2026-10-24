from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from datetime import datetime, timedelta
import random
from models import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = 'dhanush_transport_secret_key_omnitransit_2026'

# Ensure database exists
init_db()

@app.context_processor
def inject_common_data():
    conn = get_db_connection()
    hubs = conn.execute("SELECT * FROM hubs ORDER BY city").fetchall()
    conn.close()
    return {'all_hubs': hubs, 'current_year': datetime.now().year}

@app.route('/')
def index():
    conn = get_db_connection()
    # Stats for homepage
    stats = {
        'total_passengers': conn.execute("SELECT COUNT(*) FROM passenger_bookings").fetchone()[0],
        'total_cargo_kg': conn.execute("SELECT COALESCE(SUM(weight_kg), 0) FROM cargo_consignments").fetchone()[0],
        'active_trips': conn.execute("SELECT COUNT(*) FROM trips WHERE status IN ('In Transit', 'Scheduled')").fetchone()[0],
        'active_fleet': conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0],
    }
    
    # Active trips with origin and destination hub names
    active_trips = conn.execute('''
        SELECT t.*, r.distance_km, r.duration_hours,
               v.name as vehicle_name, v.vehicle_type, v.reg_number, v.total_seats, v.total_cargo_kg,
               h1.city as origin_city, h1.code as origin_code,
               h2.city as dest_city, h2.code as dest_code
        FROM trips t
        JOIN routes r ON t.route_id = r.id
        JOIN vehicles v ON t.vehicle_id = v.id
        JOIN hubs h1 ON r.origin_hub_id = h1.id
        JOIN hubs h2 ON r.dest_hub_id = h2.id
        ORDER BY t.departure_time DESC
        LIMIT 4
    ''').fetchall()
    
    conn.close()
    return render_template('index.html', stats=stats, active_trips=active_trips)

# ----------------- PASSENGER ROUTES ----------------- #

@app.route('/passenger', methods=['GET', 'POST'])
def passenger_portal():
    conn = get_db_connection()
    trips = []
    selected_origin = request.args.get('origin', type=int)
    selected_dest = request.args.get('dest', type=int)
    
    query = '''
        SELECT t.*, r.distance_km, r.duration_hours, r.base_passenger_fare,
               v.name as vehicle_name, v.vehicle_type, v.reg_number, v.total_seats, v.total_cargo_kg,
               v.driver_name, v.driver_phone,
               h1.city as origin_city, h1.name as origin_hub_name,
               h2.city as dest_city, h2.name as dest_hub_name
        FROM trips t
        JOIN routes r ON t.route_id = r.id
        JOIN vehicles v ON t.vehicle_id = v.id
        JOIN hubs h1 ON r.origin_hub_id = h1.id
        JOIN hubs h2 ON r.dest_hub_id = h2.id
        WHERE v.total_seats > 0
    '''
    params = []
    if selected_origin and selected_dest:
        query += ' AND r.origin_hub_id = ? AND r.dest_hub_id = ?'
        params.extend([selected_origin, selected_dest])
        
    query += ' ORDER BY t.departure_time ASC'
    trips = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('passenger_book.html', trips=trips, selected_origin=selected_origin, selected_dest=selected_dest)

@app.route('/passenger/book', methods=['POST'])
def book_passenger():
    trip_id = request.form.get('trip_id', type=int)
    name = request.form.get('passenger_name', '').strip()
    phone = request.form.get('passenger_phone', '').strip()
    email = request.form.get('passenger_email', '').strip()
    seat_number = request.form.get('seat_number', '').strip()
    
    if not (trip_id and name and phone and seat_number):
        flash('Please fill in all required passenger details.', 'danger')
        return redirect(url_for('passenger_portal'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get trip details & vehicle capacity
    trip = cursor.execute('''
        SELECT t.*, r.base_passenger_fare, v.total_seats, h1.city as origin_city, h2.city as dest_city
        FROM trips t
        JOIN routes r ON t.route_id = r.id
        JOIN vehicles v ON t.vehicle_id = v.id
        JOIN hubs h1 ON r.origin_hub_id = h1.id
        JOIN hubs h2 ON r.dest_hub_id = h2.id
        WHERE t.id = ?
    ''', (trip_id,)).fetchone()
    
    if not trip:
        flash('Selected trip was not found.', 'danger')
        conn.close()
        return redirect(url_for('passenger_portal'))
        
    if trip['booked_seats'] >= trip['total_seats']:
        flash('Sorry, this trip is already sold out for passengers.', 'danger')
        conn.close()
        return redirect(url_for('passenger_portal'))
        
    # Generate unique PNR
    pnr = f"PNR-DT-{random.randint(100000, 999999)}"
    fare = trip['base_passenger_fare']
    booked_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    qr_code = f"QR-{pnr}-{name[:4].upper()}"
    
    # Insert Booking
    cursor.execute('''
        INSERT INTO passenger_bookings (pnr, trip_id, passenger_name, passenger_phone, passenger_email, seat_number, fare_amount, status, booked_at, qr_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Confirmed', ?, ?)
    ''', (pnr, trip_id, name, phone, email, seat_number, fare, booked_at, qr_code))
    
    # Update trip booked seats
    cursor.execute('UPDATE trips SET booked_seats = booked_seats + 1 WHERE id = ?', (trip_id,))
    
    # Add initial tracking milestone
    cursor.execute('''
        INSERT INTO tracking_checkpoints (tracking_ref, ref_type, stage_name, location, status_timestamp, notes, is_completed)
        VALUES (?, 'PASSENGER', 'Ticket Confirmed & Seat Reserved', ?, ?, ?, 1)
    ''', (pnr, f"{trip['origin_city']} Hub", booked_at, f"Seat {seat_number} confirmed for {trip['origin_city']} to {trip['dest_city']}"))
    
    conn.commit()
    conn.close()
    
    flash(f"Booking confirmed! Your PNR is {pnr}", "success")
    return redirect(url_for('passenger_ticket', pnr=pnr))

@app.route('/passenger/ticket/<pnr>')
def passenger_ticket(pnr):
    conn = get_db_connection()
    booking = conn.execute('''
        SELECT b.*, t.trip_code, t.departure_time, t.arrival_time, t.status as trip_status,
               v.name as vehicle_name, v.reg_number, v.vehicle_type, v.driver_name, v.driver_phone,
               h1.city as origin_city, h1.name as origin_hub_name, h1.address as origin_address,
               h2.city as dest_city, h2.name as dest_hub_name, h2.address as dest_address,
               r.distance_km, r.duration_hours
        FROM passenger_bookings b
        JOIN trips t ON b.trip_id = t.id
        JOIN routes r ON t.route_id = r.id
        JOIN vehicles v ON t.vehicle_id = v.id
        JOIN hubs h1 ON r.origin_hub_id = h1.id
        JOIN hubs h2 ON r.dest_hub_id = h2.id
        WHERE b.pnr = ?
    ''', (pnr,)).fetchone()
    conn.close()
    
    if not booking:
        flash('Ticket not found for PNR: ' + pnr, 'warning')
        return redirect(url_for('passenger_portal'))
        
    return render_template('passenger_ticket.html', booking=booking)

# ----------------- LOGISTICS / CARGO ROUTES ----------------- #

@app.route('/cargo', methods=['GET'])
def cargo_portal():
    conn = get_db_connection()
    # List active passenger trips with available cargo payload (Cargo-Hitch capable)
    hitch_trips = conn.execute('''
        SELECT t.*, r.distance_km, r.base_cargo_rate_kg,
               v.name as vehicle_name, v.vehicle_type, v.reg_number, v.total_cargo_kg,
               (v.total_cargo_kg - t.booked_cargo_kg) as available_cargo_kg,
               h1.city as origin_city, h2.city as dest_city
        FROM trips t
        JOIN routes r ON t.route_id = r.id
        JOIN vehicles v ON t.vehicle_id = v.id
        JOIN hubs h1 ON r.origin_hub_id = h1.id
        JOIN hubs h2 ON r.dest_hub_id = h2.id
        WHERE v.vehicle_type LIKE '%Passenger%' OR v.vehicle_type LIKE '%Minivan%'
        ORDER BY t.departure_time ASC
    ''').fetchall()
    conn.close()
    return render_template('cargo_book.html', hitch_trips=hitch_trips)

@app.route('/cargo/book', methods=['POST'])
def book_cargo():
    origin_hub_id = request.form.get('origin_hub_id', type=int)
    dest_hub_id = request.form.get('dest_hub_id', type=int)
    sender_name = request.form.get('sender_name', '').strip()
    sender_phone = request.form.get('sender_phone', '').strip()
    sender_address = request.form.get('sender_address', '').strip()
    receiver_name = request.form.get('receiver_name', '').strip()
    receiver_phone = request.form.get('receiver_phone', '').strip()
    receiver_address = request.form.get('receiver_address', '').strip()
    weight_kg = request.form.get('weight_kg', type=float)
    cargo_type = request.form.get('cargo_type', 'General Parcel')
    preferred_mode = request.form.get('preferred_mode', 'Auto') # Auto, Cargo-Hitch, Dedicated Freight
    
    if not (origin_hub_id and dest_hub_id and sender_name and receiver_name and weight_kg):
        flash('Please fill in all mandatory cargo shipping details.', 'danger')
        return redirect(url_for('cargo_portal'))
        
    if origin_hub_id == dest_hub_id:
        flash('Origin and Destination terminals cannot be identical.', 'danger')
        return redirect(url_for('cargo_portal'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find route details
    route = cursor.execute('''
        SELECT * FROM routes WHERE origin_hub_id = ? AND dest_hub_id = ?
    ''', (origin_hub_id, dest_hub_id)).fetchone()
    
    if not route:
        flash('No direct route configured between these selected terminals currently.', 'danger')
        conn.close()
        return redirect(url_for('cargo_portal'))
        
    # Smart Dual-Transit Dispatch Logic:
    # Check if this consignment fits into a scheduled passenger vehicle's spare cargo bay!
    assigned_trip = None
    final_transport_mode = 'Dedicated Heavy Freight'
    rate_multiplier = 1.0
    
    # If package is <= 150 kg, it qualifies for high-speed Cargo Hitching on passenger buses!
    if weight_kg <= 150.0 and preferred_mode != 'Dedicated Heavy Freight':
        candidate_trip = cursor.execute('''
            SELECT t.*, v.total_cargo_kg, (v.total_cargo_kg - t.booked_cargo_kg) as spare_capacity
            FROM trips t
            JOIN vehicles v ON t.vehicle_id = v.id
            WHERE t.route_id = ? 
              AND t.status IN ('Scheduled', 'Boarding & Loading', 'In Transit')
              AND (v.total_cargo_kg - t.booked_cargo_kg) >= ?
              AND (v.vehicle_type LIKE '%Passenger%' OR v.vehicle_type LIKE '%Minivan%')
            ORDER BY t.departure_time ASC
            LIMIT 1
        ''', (route['id'], weight_kg)).fetchone()
        
        if candidate_trip:
            assigned_trip = candidate_trip
            final_transport_mode = 'Cargo-Hitch (Express via Passenger Fleet)'
            rate_multiplier = 1.15 # Express passenger hitch premium
            
    # If not hitched, assign to dedicated freight trip or schedule
    if not assigned_trip:
        freight_trip = cursor.execute('''
            SELECT t.*, v.total_cargo_kg, (v.total_cargo_kg - t.booked_cargo_kg) as spare_capacity
            FROM trips t
            JOIN vehicles v ON t.vehicle_id = v.id
            WHERE t.route_id = ? 
              AND (v.total_cargo_kg - t.booked_cargo_kg) >= ?
              AND v.vehicle_type LIKE '%Freight%'
            ORDER BY t.departure_time ASC
            LIMIT 1
        ''', (route['id'], weight_kg)).fetchone()
        if freight_trip:
            assigned_trip = freight_trip
            final_transport_mode = 'Dedicated Heavy Freight'

    # Pricing calculation
    base_price = (weight_kg * route['base_cargo_rate_kg']) * rate_multiplier
    if base_price < 250:
        base_price = 250.0 # Minimum consignment booking fee
    price_amount = round(base_price, 2)
    
    awb = f"AWB-DT-{random.randint(10000, 99999)}"
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    volume_cbm = round(weight_kg * 0.005, 3)
    
    trip_id = assigned_trip['id'] if assigned_trip else None
    
    cursor.execute('''
        INSERT INTO cargo_consignments (
            awb, trip_id, origin_hub_id, dest_hub_id, sender_name, sender_phone, sender_address,
            receiver_name, receiver_phone, receiver_address, weight_kg, volume_cbm, cargo_type,
            transport_mode, price_amount, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Booked', ?)
    ''', (awb, trip_id, origin_hub_id, dest_hub_id, sender_name, sender_phone, sender_address,
          receiver_name, receiver_phone, receiver_address, weight_kg, volume_cbm, cargo_type,
          final_transport_mode, price_amount, now_str))
          
    if trip_id:
        cursor.execute('UPDATE trips SET booked_cargo_kg = booked_cargo_kg + ? WHERE id = ?', (weight_kg, trip_id))

    # Origin hub name
    origin_hub = cursor.execute('SELECT * FROM hubs WHERE id = ?', (origin_hub_id,)).fetchone()
    
    # Initial Checkpoints
    cursor.execute('''
        INSERT INTO tracking_checkpoints (tracking_ref, ref_type, stage_name, location, status_timestamp, notes, is_completed)
        VALUES (?, 'CARGO', 'Consignment Booked & Waybill Issued', ?, ?, ?, 1)
    ''', (awb, f"{origin_hub['city']} Hub", now_str, f"Shipment of {weight_kg} kg registered under {final_transport_mode}"))
    
    if assigned_trip:
        cursor.execute('''
            INSERT INTO tracking_checkpoints (tracking_ref, ref_type, stage_name, location, status_timestamp, notes, is_completed)
            VALUES (?, 'CARGO', 'Allocated to Vehicle Cargo Bay', ?, ?, ?, 1)
        ''', (awb, f"{origin_hub['city']} Hub", now_str, f"Dispatched on Trip {assigned_trip['trip_code']}"))

    conn.commit()
    conn.close()
    
    flash(f"Consignment booked! AWB Tracking Code: {awb} (Allocated to: {final_transport_mode})", "success")
    return redirect(url_for('cargo_receipt', awb=awb))

@app.route('/cargo/receipt/<awb>')
def cargo_receipt(awb):
    conn = get_db_connection()
    cargo = conn.execute('''
        SELECT c.*, 
               h1.city as origin_city, h1.name as origin_hub_name, h1.phone as origin_phone,
               h2.city as dest_city, h2.name as dest_hub_name, h2.phone as dest_phone,
               t.trip_code, t.departure_time, t.arrival_time,
               v.name as vehicle_name, v.reg_number, v.vehicle_type, v.driver_name, v.driver_phone
        FROM cargo_consignments c
        JOIN hubs h1 ON c.origin_hub_id = h1.id
        JOIN hubs h2 ON c.dest_hub_id = h2.id
        LEFT JOIN trips t ON c.trip_id = t.id
        LEFT JOIN vehicles v ON t.vehicle_id = v.id
        WHERE c.awb = ?
    ''', (awb,)).fetchone()
    conn.close()
    
    if not cargo:
        flash('Consignment not found for AWB: ' + awb, 'warning')
        return redirect(url_for('cargo_portal'))
        
    return render_template('cargo_receipt.html', cargo=cargo)

# ----------------- UNIVERSAL TRACKING & LIVE MAP ----------------- #

@app.route('/track', methods=['GET'])
def tracking_search():
    ref = request.args.get('ref', '').strip()
    if ref:
        return redirect(url_for('tracking_details', tracking_ref=ref))
    return render_template('tracking.html', item=None)

@app.route('/track/<tracking_ref>')
def tracking_details(tracking_ref):
    conn = get_db_connection()
    
    tracking_ref = tracking_ref.strip()
    item = None
    item_type = None
    
    # 1. Search Passenger Bookings
    passenger = conn.execute('''
        SELECT b.pnr as code, b.passenger_name as title_name, b.status, b.seat_number, b.fare_amount,
               b.booked_at as created_date,
               t.id as trip_id, t.trip_code, t.departure_time, t.arrival_time, t.status as trip_status,
               t.current_lat, t.current_lng, t.progress_pct, t.booked_seats, t.booked_cargo_kg,
               v.name as vehicle_name, v.reg_number, v.vehicle_type, v.driver_name, v.driver_phone,
               v.total_seats, v.total_cargo_kg,
               h1.city as origin_city, h1.name as origin_hub, h1.lat as origin_lat, h1.lng as origin_lng,
               h2.city as dest_city, h2.name as dest_hub, h2.lat as dest_lat, h2.lng as dest_lng
        FROM passenger_bookings b
        JOIN trips t ON b.trip_id = t.id
        JOIN routes r ON t.route_id = r.id
        JOIN vehicles v ON t.vehicle_id = v.id
        JOIN hubs h1 ON r.origin_hub_id = h1.id
        JOIN hubs h2 ON r.dest_hub_id = h2.id
        WHERE b.pnr = ?
    ''', (tracking_ref,)).fetchone()
    
    if passenger:
        item = dict(passenger)
        item_type = 'PASSENGER'
    else:
        # 2. Search Cargo Consignments
        cargo = conn.execute('''
            SELECT c.awb as code, c.cargo_type as title_name, c.status, c.weight_kg, c.price_amount,
                   c.sender_name, c.receiver_name, c.transport_mode, c.created_at as created_date,
                   t.id as trip_id, t.trip_code, t.departure_time, t.arrival_time, t.status as trip_status,
                   t.current_lat, t.current_lng, t.progress_pct, t.booked_seats, t.booked_cargo_kg,
                   v.name as vehicle_name, v.reg_number, v.vehicle_type, v.driver_name, v.driver_phone,
                   v.total_seats, v.total_cargo_kg,
                   h1.city as origin_city, h1.name as origin_hub, h1.lat as origin_lat, h1.lng as origin_lng,
                   h2.city as dest_city, h2.name as dest_hub, h2.lat as dest_lat, h2.lng as dest_lng
            FROM cargo_consignments c
            JOIN hubs h1 ON c.origin_hub_id = h1.id
            JOIN hubs h2 ON c.dest_hub_id = h2.id
            LEFT JOIN trips t ON c.trip_id = t.id
            LEFT JOIN routes r ON t.route_id = r.id
            LEFT JOIN vehicles v ON t.vehicle_id = v.id
            WHERE c.awb = ?
        ''', (tracking_ref,)).fetchone()
        
        if cargo:
            item = dict(cargo)
            item_type = 'CARGO'

    if not item:
        conn.close()
        flash(f"No active record found for tracking reference '{tracking_ref}'. Please verify your PNR or AWB number.", "warning")
        return render_template('tracking.html', item=None, tracking_ref=tracking_ref)
        
    # Get Checkpoints
    checkpoints = conn.execute('''
        SELECT * FROM tracking_checkpoints 
        WHERE tracking_ref = ? 
        ORDER BY id ASC
    ''', (tracking_ref,)).fetchall()
    
    # Also fetch dual transit context (if on a hybrid bus carrying both)
    dual_manifest = None
    if item.get('trip_id'):
        co_passengers = conn.execute('''
            SELECT COUNT(*) FROM passenger_bookings WHERE trip_id = ?
        ''', (item['trip_id'],)).fetchone()[0]
        
        co_cargo = conn.execute('''
            SELECT COUNT(*), COALESCE(SUM(weight_kg), 0) FROM cargo_consignments WHERE trip_id = ?
        ''', (item['trip_id'],)).fetchone()
        
        dual_manifest = {
            'passenger_count': co_passengers,
            'cargo_consignments_count': co_cargo[0],
            'cargo_weight_kg': co_cargo[1]
        }
        
    conn.close()
    return render_template('tracking.html', item=item, item_type=item_type, checkpoints=checkpoints, dual_manifest=dual_manifest, tracking_ref=tracking_ref)

# ----------------- FLEET DISPATCH & CONTROLS ----------------- #

@app.route('/fleet')
def fleet_control():
    conn = get_db_connection()
    trips = conn.execute('''
        SELECT t.*, r.distance_km, r.duration_hours,
               v.name as vehicle_name, v.vehicle_type, v.reg_number, v.total_seats, v.total_cargo_kg,
               v.driver_name, v.driver_phone,
               h1.city as origin_city, h1.name as origin_hub_name,
               h2.city as dest_city, h2.name as dest_hub_name
        FROM trips t
        JOIN routes r ON t.route_id = r.id
        JOIN vehicles v ON t.vehicle_id = v.id
        JOIN hubs h1 ON r.origin_hub_id = h1.id
        JOIN hubs h2 ON r.dest_hub_id = h2.id
        ORDER BY t.status DESC, t.id ASC
    ''').fetchall()
    
    fleet_summary = {
        'total_vehicles': conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0],
        'hybrid_coaches': conn.execute("SELECT COUNT(*) FROM vehicles WHERE vehicle_type LIKE '%Passenger%'").fetchone()[0],
        'freight_trucks': conn.execute("SELECT COUNT(*) FROM vehicles WHERE vehicle_type LIKE '%Freight%'").fetchone()[0],
        'active_in_transit': conn.execute("SELECT COUNT(*) FROM trips WHERE status = 'In Transit'").fetchone()[0]
    }
    conn.close()
    return render_template('fleet_dispatch.html', trips=trips, summary=fleet_summary)

@app.route('/fleet/simulate-step/<int:trip_id>', methods=['POST'])
def simulate_trip_progress(trip_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    trip = cursor.execute('''
        SELECT t.*, r.distance_km,
               h1.city as origin_city, h1.lat as o_lat, h1.lng as o_lng,
               h2.city as dest_city, h2.lat as d_lat, h2.lng as d_lng
        FROM trips t
        JOIN routes r ON t.route_id = r.id
        JOIN hubs h1 ON r.origin_hub_id = h1.id
        JOIN hubs h2 ON r.dest_hub_id = h2.id
        WHERE t.id = ?
    ''', (trip_id,)).fetchone()
    
    if not trip:
        conn.close()
        flash("Trip not found", "danger")
        return redirect(url_for('fleet_control'))
        
    current_pct = trip['progress_pct']
    new_pct = min(100, current_pct + 15)
    
    # Calculate intermediate GPS coordinates based on linear interpolation along route
    ratio = new_pct / 100.0
    new_lat = trip['o_lat'] + (trip['d_lat'] - trip['o_lat']) * ratio
    new_lng = trip['o_lng'] + (trip['d_lng'] - trip['o_lng']) * ratio
    
    new_status = 'In Transit'
    if new_pct >= 100:
        new_status = 'Completed'
        
    cursor.execute('''
        UPDATE trips 
        SET progress_pct = ?, current_lat = ?, current_lng = ?, status = ?
        WHERE id = ?
    ''', (new_pct, round(new_lat, 4), round(new_lng, 4), new_status, trip_id))
    
    # Update checkpoint for all passengers and hitched cargo on this trip!
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    checkpoint_desc = f"Vehicle reached {new_pct}% waypoint along {trip['origin_city']} - {trip['dest_city']} corridor."
    if new_pct >= 100:
        checkpoint_desc = f"Safely docked at {trip['dest_city']} Terminal. Ready for passenger disembarkation and cargo unloading."

    # Update passenger milestones
    passengers = cursor.execute('SELECT pnr FROM passenger_bookings WHERE trip_id = ?', (trip_id,)).fetchall()
    for p in passengers:
        cursor.execute('''
            INSERT INTO tracking_checkpoints (tracking_ref, ref_type, stage_name, location, status_timestamp, notes, is_completed)
            VALUES (?, 'PASSENGER', ?, ?, ?, ?, 1)
        ''', (p['pnr'], 'Waypoint Milestone Reached' if new_pct < 100 else 'Trip Destination Arrival', f"Corridor at {new_pct}%", now_str, checkpoint_desc))
        if new_pct >= 100:
            cursor.execute("UPDATE passenger_bookings SET status = 'Completed' WHERE pnr = ?", (p['pnr'],))

    # Update cargo milestones
    cargos = cursor.execute('SELECT awb FROM cargo_consignments WHERE trip_id = ?', (trip_id,)).fetchall()
    for c in cargos:
        cursor.execute('''
            INSERT INTO tracking_checkpoints (tracking_ref, ref_type, stage_name, location, status_timestamp, notes, is_completed)
            VALUES (?, 'CARGO', ?, ?, ?, ?, 1)
        ''', (c['awb'], 'Highway In-Transit Ping' if new_pct < 100 else 'Arrived at Destination Hub', f"Waypoint {new_pct}%", now_str, checkpoint_desc))
        if new_pct >= 100:
            cursor.execute("UPDATE cargo_consignments SET status = 'Arrived at Hub' WHERE awb = ?", (c['awb'],))
            
    conn.commit()
    conn.close()
    
    flash(f"Simulated advance for {trip['trip_code']}: Now at {new_pct}% completion ({new_status})!", "success")
    return redirect(url_for('fleet_control'))

# ----------------- ANALYTICS & DUAL TRANSIT IMPACT ----------------- #

@app.route('/analytics')
def analytics():
    conn = get_db_connection()
    
    passenger_rev = conn.execute("SELECT COALESCE(SUM(fare_amount), 0) FROM passenger_bookings").fetchone()[0]
    cargo_rev = conn.execute("SELECT COALESCE(SUM(price_amount), 0) FROM cargo_consignments").fetchone()[0]
    total_rev = passenger_rev + cargo_rev
    
    hitched_cargo_count = conn.execute("SELECT COUNT(*) FROM cargo_consignments WHERE transport_mode LIKE '%Cargo-Hitch%'").fetchone()[0]
    hitched_cargo_weight = conn.execute("SELECT COALESCE(SUM(weight_kg), 0) FROM cargo_consignments WHERE transport_mode LIKE '%Cargo-Hitch%'").fetchone()[0]
    
    # Calculate CO2 saved: 
    # Average 0.18 kg CO2 per ton-km saved by utilizing spare bus capacity instead of running an extra van
    # Assuming average 400km journey
    co2_saved_kg = round((hitched_cargo_weight / 1000.0) * 400.0 * 0.18, 1)
    
    route_stats = conn.execute('''
        SELECT r.route_code, h1.city as origin, h2.city as dest,
               COUNT(DISTINCT pb.id) as total_passengers,
               COUNT(DISTINCT cc.id) as total_cargos,
               COALESCE(SUM(pb.fare_amount), 0) as route_passenger_rev,
               COALESCE(SUM(cc.price_amount), 0) as route_cargo_rev
        FROM routes r
        JOIN hubs h1 ON r.origin_hub_id = h1.id
        JOIN hubs h2 ON r.dest_hub_id = h2.id
        LEFT JOIN trips t ON t.route_id = r.id
        LEFT JOIN passenger_bookings pb ON pb.trip_id = t.id
        LEFT JOIN cargo_consignments cc ON cc.trip_id = t.id
        GROUP BY r.id
    ''').fetchall()
    
    conn.close()
    
    data = {
        'passenger_rev': passenger_rev,
        'cargo_rev': cargo_rev,
        'total_rev': total_rev,
        'hitched_cargo_count': hitched_cargo_count,
        'hitched_cargo_weight': hitched_cargo_weight,
        'co2_saved_kg': co2_saved_kg,
        'route_stats': route_stats
    }
    return render_template('analytics.html', data=data)

# ----------------- API ENDPOINTS ----------------- #

@app.route('/api/trip/<int:trip_id>')
def api_trip_details(trip_id):
    conn = get_db_connection()
    trip = conn.execute('''
        SELECT t.*, v.name as vehicle_name, v.total_seats, v.total_cargo_kg,
               h1.city as origin_city, h2.city as dest_city
        FROM trips t
        JOIN vehicles v ON t.vehicle_id = v.id
        JOIN routes r ON t.route_id = r.id
        JOIN hubs h1 ON r.origin_hub_id = h1.id
        JOIN hubs h2 ON r.dest_hub_id = h2.id
        WHERE t.id = ?
    ''', (trip_id,)).fetchone()
    
    if not trip:
        conn.close()
        return jsonify({'error': 'Trip not found'}), 404
        
    passengers = conn.execute('SELECT seat_number, status FROM passenger_bookings WHERE trip_id = ?', (trip_id,)).fetchall()
    conn.close()
    
    return jsonify({
        'trip': dict(trip),
        'booked_seats': [p['seat_number'] for p in passengers]
    })

if __name__ == '__main__':
    print("=============================================================")
    print("   DHANUSH OMNITRANSIT & LOGISTICS (DOTL) PLATFORM")
    print("   Dual-Transit: Passengers + Freight Cargo hitched network")
    print("   Running on http://127.0.0.1:5000")
    print("=============================================================")
    app.run(host='0.0.0.0', port=5000, debug=True)
